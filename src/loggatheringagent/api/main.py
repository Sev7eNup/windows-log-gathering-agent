"""
FastAPI server for the Windows Log Gathering Agent.
Provides REST API endpoints and chatbot interface.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import structlog

from ..config.settings import Settings
from ..core.log_collector import WindowsLogCollector, ClientLogCollection
from ..core.llm_analyzer import WindowsLogAnalyzer, ClientAnalysisResult

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global settings
settings = Settings()

# Create FastAPI app
app = FastAPI(
    title="Windows Log Gathering Agent",
    description="Centralized log collection and LLM analysis for Windows deployment troubleshooting",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
log_collector = WindowsLogCollector(settings)
log_analyzer = WindowsLogAnalyzer(settings)

# In-memory storage for analysis results (in production, use database)
analysis_cache: Dict[str, Dict[str, Any]] = {}


# Pydantic models for API
class AnalysisRequest(BaseModel):
    client_names: List[str]
    include_summary: bool = True
    force_refresh: bool = False


class ClientStatus(BaseModel):
    name: str
    hostname: str
    status: str  # "healthy", "issues", "critical", "unknown"
    last_analyzed: Optional[datetime] = None


class AnalysisResponse(BaseModel):
    request_id: str
    status: str  # "completed", "running", "failed"
    clients_analyzed: List[str]
    results: List[Dict[str, Any]]
    summary: Optional[str] = None
    timestamp: datetime


class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    suggestions: List[str]
    analysis_triggered: bool = False
    client_names: List[str] = []


# Dependency to get settings
def get_settings():
    return settings


# Health check endpoint
@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with system metrics."""
    try:
        # Calculate uptime
        import time
        import psutil
        
        # Get system uptime (in seconds since server start)
        current_time = datetime.now()
        if not hasattr(health_check, 'start_time'):
            health_check.start_time = current_time
        uptime_seconds = int((current_time - health_check.start_time).total_seconds())
        
        # Get number of configured clients
        try:
            machines_config = settings.load_machines_config()
            configured_clients = len(machines_config.clients)
        except:
            configured_clients = 0
        
        # Get number of clients with recent analysis
        clients_with_analysis = len([k for k in analysis_cache.keys() if not k.startswith('analysis_')])
        
        # Find last analysis time
        last_analysis = None
        for cache_key, cache_value in analysis_cache.items():
            if isinstance(cache_value, dict) and 'timestamp' in cache_value:
                analysis_time = cache_value['timestamp']
                if isinstance(analysis_time, str):
                    try:
                        analysis_time = datetime.fromisoformat(analysis_time.replace('Z', '+00:00'))
                    except:
                        continue
                if last_analysis is None or analysis_time > last_analysis:
                    last_analysis = analysis_time
        
        # Get system memory usage
        try:
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent
            cpu_usage = psutil.cpu_percent(interval=0.1)
        except:
            memory_usage_percent = 0
            cpu_usage = 0
        
        # Test LLM connection (quick check without full request)
        llm_status = "unknown"
        try:
            import httpx
            machines_config = settings.load_machines_config()
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{machines_config.llm_config.endpoint}/v1/models")
                if response.status_code == 200:
                    llm_status = "connected"
                else:
                    llm_status = "error"
        except:
            llm_status = "offline"
        
        return {
            "status": "healthy",
            "uptime": uptime_seconds,
            "connected_clients": configured_clients,
            "active_clients": clients_with_analysis,
            "last_analysis": last_analysis.isoformat() if last_analysis else None,
            "llm_status": llm_status,
            "system_metrics": {
                "memory_usage_percent": memory_usage_percent,
                "cpu_usage_percent": cpu_usage,
                "active_analyses": len([k for k in analysis_cache.keys() if k.startswith('analysis_')]),
                "cache_size": len(analysis_cache)
            },
            "timestamp": current_time
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.now(),
            "uptime": 0,
            "connected_clients": 0,
            "last_analysis": None
        }


# List available clients
@app.get("/clients", response_model=List[ClientStatus])
async def list_clients():
    """Get list of configured client machines."""
    try:
        machines_config = settings.load_machines_config()
        client_statuses = []
        
        for client in machines_config.clients:
            # Check if we have recent analysis
            last_analyzed = None
            status = "unknown"
            
            if client.name in analysis_cache:
                cache_entry = analysis_cache[client.name]
                last_analyzed = cache_entry.get("timestamp")
                status = cache_entry.get("overall_status", "unknown")
            
            client_statuses.append(ClientStatus(
                name=client.name,
                hostname=client.hostname,
                status=status,
                last_analyzed=last_analyzed
            ))
        
        return client_statuses
        
    except Exception as e:
        logger.error("Error listing clients", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error listing clients: {str(e)}")


# Start log analysis
@app.post("/analyze", response_model=Dict[str, str])
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Start log analysis for specified clients."""
    try:
        request_id = f"analysis_{int(datetime.now().timestamp())}"
        
        logger.info("Starting analysis", 
                   request_id=request_id, 
                   clients=request.client_names,
                   force_refresh=request.force_refresh)
        
        # Add background task
        background_tasks.add_task(
            run_analysis, 
            request_id, 
            request.client_names, 
            request.include_summary,
            request.force_refresh
        )
        
        return {
            "request_id": request_id,
            "status": "started",
            "message": f"Analysis started for {len(request.client_names)} clients"
        }
        
    except Exception as e:
        logger.error("Error starting analysis", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error starting analysis: {str(e)}")


# Get analysis results
@app.get("/analyze/{request_id}")
async def get_analysis_results(request_id: str):
    """Get analysis results by request ID."""
    try:
        # Check if results are available (in production, query database)
        if request_id in analysis_cache:
            result = analysis_cache[request_id]
            logger.info("Retrieved analysis result", 
                       request_id=request_id, 
                       status=result.get("status", "unknown"))
            return result
        else:
            # Analysis might be in progress or not found
            logger.warning("Analysis result not found in cache", request_id=request_id)
            return {
                "request_id": request_id,
                "status": "not_found",
                "message": "Analysis results not found - it may still be in progress or has expired"
            }
            
    except Exception as e:
        logger.error("Error retrieving analysis results", 
                    request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")


# Get specific client analysis
@app.get("/clients/{client_name}/analysis")
async def get_client_analysis(client_name: str):
    """Get latest analysis results for a specific client."""
    try:
        if client_name in analysis_cache:
            return analysis_cache[client_name]
        else:
            raise HTTPException(status_code=404, detail=f"No analysis found for client: {client_name}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving client analysis", 
                    client_name=client_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error retrieving analysis: {str(e)}")


# Collect logs from a specific client
@app.post("/api/collect/{client_name}")
async def collect_client_logs(client_name: str):
    """Collect logs from a specific client machine."""
    try:
        logger.info("Starting log collection", client_name=client_name)
        
        # Initialize settings and collector
        settings = Settings()
        collector = WindowsLogCollector(settings)
        
        # Collect logs
        result = await collector.collect_client_logs(client_name)
        
        # Convert to API response format
        response = {
            "client_name": result.client_name,
            "hostname": result.hostname,
            "success": result.success,
            "timestamp": result.timestamp.isoformat(),
            "log_results": [
                {
                    "source": log_result.source,
                    "success": log_result.success,
                    "content": log_result.content if log_result.success else "",
                    "error": log_result.error,
                    "lines_count": log_result.lines_count,
                    "timestamp": log_result.timestamp.isoformat()
                }
                for log_result in result.log_results
            ],
            "errors": result.errors
        }
        
        logger.info("Log collection completed", 
                   client_name=client_name, 
                   success=result.success,
                   results_count=len(result.log_results),
                   errors_count=len(result.errors))
        
        return response
        
    except Exception as e:
        logger.error("Error collecting logs", 
                    client_name=client_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Log collection failed: {str(e)}")


# Quick analyze single client
@app.post("/clients/{client_name}/analyze")
async def analyze_single_client(client_name: str, background_tasks: BackgroundTasks):
    """Quick analysis of a single client."""
    try:
        request_id = f"single_{client_name}_{int(datetime.now().timestamp())}"
        
        logger.info("Starting single client analysis", 
                   client_name=client_name, request_id=request_id)
        
        background_tasks.add_task(run_analysis, request_id, [client_name], True, True)
        
        return {
            "request_id": request_id,
            "client_name": client_name,
            "status": "started"
        }
        
    except Exception as e:
        logger.error("Error starting single client analysis", 
                    client_name=client_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Chatbot endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(message: ChatMessage, background_tasks: BackgroundTasks):
    """Chat interface for interacting with the log analysis system."""
    try:
        logger.info("Chat message received", message=message.message)
        
        response = await process_chat_message(message.message, message.context, background_tasks)
        return response
        
    except Exception as e:
        logger.error("Error processing chat message", error=str(e))
        return ChatResponse(
            response=f"I encountered an error processing your request: {str(e)}",
            suggestions=["Try rephrasing your question", "Check system status"],
            analysis_triggered=False
        )


# Simple web interface
@app.get("/", response_class=HTMLResponse)
async def web_interface():
    """Enhanced web interface with real-time logging."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Windows Log Gathering Agent</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .left-panel { }
            .right-panel { }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ccc; border-radius: 5px; }
            .button-group { display: flex; gap: 10px; flex-wrap: wrap; }
            button { padding: 10px 20px; margin: 5px 0; cursor: pointer; border: none; border-radius: 3px; }
            .btn-primary { background: #007bff; color: white; }
            .btn-success { background: #28a745; color: white; }
            .btn-warning { background: #ffc107; color: black; }
            .btn-info { background: #17a2b8; color: white; }
            button:hover { opacity: 0.8; }
            pre { background: #f5f5f5; padding: 15px; overflow-x: auto; border-radius: 3px; }
            input, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ccc; border-radius: 3px; }
            #logWindow { 
                height: 400px; 
                overflow-y: auto; 
                background: #1e1e1e; 
                color: #00ff00; 
                padding: 15px; 
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
            }
            .log-entry { margin-bottom: 5px; }
            .log-info { color: #00ff00; }
            .log-warning { color: #ffff00; }
            .log-error { color: #ff0000; }
            .log-debug { color: #888888; }
            .status-indicator { 
                display: inline-block; 
                width: 10px; 
                height: 10px; 
                border-radius: 50%; 
                margin-right: 5px; 
            }
            .status-success { background: #28a745; }
            .status-warning { background: #ffc107; }
            .status-error { background: #dc3545; }
            .status-info { background: #17a2b8; }
            #chatResponse { 
                background: #f8f9fa; 
                padding: 15px; 
                border-radius: 3px; 
                margin-top: 10px;
                border-left: 4px solid #007bff;
            }
        </style>
    </head>
    <body>
        <h1>🖥️ Windows Log Gathering Agent</h1>
        
        <div class="container">
            <div class="left-panel">
                <div class="section">
                    <h2>🚀 Quick Actions</h2>
                    <div class="button-group">
                        <button class="btn-info" onclick="listClients()">📋 List Clients</button>
                        <button class="btn-success" onclick="analyzeAll()">🔍 Analyze All</button>
                        <button class="btn-primary" onclick="checkHealth()">💚 Health Check</button>
                        <button class="btn-warning" onclick="clearLogs()">🗑️ Clear Logs</button>
                    </div>
                </div>
                
                <div class="section">
                    <h2>💬 Chat Interface</h2>
                    <textarea id="chatInput" placeholder="Ask about log analysis, client status, or request specific analysis..." rows="3"></textarea>
                    <button class="btn-primary" onclick="sendChatMessage()">Send Message</button>
                    <div id="chatResponse"></div>
                </div>
                
                <div class="section">
                    <h2>📊 Results</h2>
                    <pre id="results">Results will appear here...</pre>
                </div>
            </div>
            
            <div class="right-panel">
                <div class="section">
                    <h2>🔍 Live Process Log</h2>
                    <div style="margin-bottom: 10px;">
                        <span class="status-indicator status-success"></span>Ready
                        <span style="float: right;">
                            <button class="btn-info" onclick="toggleAutoScroll()">Auto-scroll: ON</button>
                        </span>
                    </div>
                    <div id="logWindow"></div>
                </div>
                
                <div class="section">
                    <h2>⚙️ System Status</h2>
                    <div id="systemStatus">
                        <div><strong>Server:</strong> <span class="status-indicator status-success"></span>Running</div>
                        <div><strong>LLM Endpoint:</strong> <span id="llmStatus">Not tested</span></div>
                        <div><strong>Last Analysis:</strong> <span id="lastAnalysis">Never</span></div>
                        <div><strong>Active Clients:</strong> <span id="activeClients">0</span></div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let autoScroll = true;
            let requestIdTracker = {};
            
            function addLog(message, type = 'info') {
                const logWindow = document.getElementById('logWindow');
                const timestamp = new Date().toLocaleTimeString();
                const logEntry = document.createElement('div');
                logEntry.className = `log-entry log-${type}`;
                logEntry.innerHTML = `[${timestamp}] ${message}`;
                logWindow.appendChild(logEntry);
                
                if (autoScroll) {
                    logWindow.scrollTop = logWindow.scrollHeight;
                }
            }
            
            function clearLogs() {
                document.getElementById('logWindow').innerHTML = '';
                addLog('Logs cleared', 'info');
            }
            
            function toggleAutoScroll() {
                autoScroll = !autoScroll;
                const btn = event.target;
                btn.textContent = `Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
                addLog(`Auto-scroll ${autoScroll ? 'enabled' : 'disabled'}`, 'debug');
            }
            
            async function apiCall(endpoint, method = 'GET', body = null, showLogs = true) {
                if (showLogs) {
                    addLog(`📡 API Call: ${method} ${endpoint}`, 'info');
                }
                
                try {
                    const options = { method };
                    if (body) {
                        options.headers = { 'Content-Type': 'application/json' };
                        options.body = JSON.stringify(body);
                        if (showLogs) {
                            addLog(`📤 Request body: ${JSON.stringify(body, null, 2)}`, 'debug');
                        }
                    }
                    
                    const response = await fetch(endpoint, options);
                    const result = await response.json();
                    
                    if (showLogs) {
                        addLog(`📥 Response (${response.status}): ${JSON.stringify(result, null, 2)}`, response.ok ? 'info' : 'error');
                    }
                    
                    return result;
                } catch (error) {
                    if (showLogs) {
                        addLog(`❌ API Error: ${error.message}`, 'error');
                    }
                    return { error: error.message };
                }
            }
            
            async function listClients() {
                addLog('🔍 Fetching client list...', 'info');
                const result = await apiCall('/clients');
                document.getElementById('results').textContent = JSON.stringify(result, null, 2);
                
                if (result.length) {
                    document.getElementById('activeClients').textContent = result.length;
                    addLog(`✅ Found ${result.length} configured clients`, 'info');
                } else {
                    addLog('⚠️ No clients configured', 'warning');
                }
            }
            
            async function analyzeAll() {
                addLog('🚀 Starting analysis process...', 'info');
                
                // First get clients
                const clients = await apiCall('/clients', 'GET', null, false);
                if (clients.error) {
                    addLog(`❌ Failed to get clients: ${clients.error}`, 'error');
                    document.getElementById('results').textContent = 'Error: ' + clients.error;
                    return;
                }
                
                addLog(`📋 Found ${clients.length} clients to analyze`, 'info');
                const clientNames = clients.map(c => c.name);
                
                // Start analysis
                addLog('🔄 Submitting analysis request...', 'info');
                const result = await apiCall('/analyze', 'POST', { 
                    client_names: clientNames, 
                    include_summary: true,
                    force_refresh: true
                });
                
                document.getElementById('results').textContent = JSON.stringify(result, null, 2);
                
                if (result.request_id) {
                    addLog(`✅ Analysis started with ID: ${result.request_id}`, 'info');
                    requestIdTracker[result.request_id] = Date.now();
                    
                    // Poll for results
                    pollAnalysisResults(result.request_id);
                } else {
                    addLog('❌ Analysis failed to start', 'error');
                }
            }
            
            async function pollAnalysisResults(requestId) {
                addLog(`🔄 Checking analysis progress for ${requestId}...`, 'debug');
                
                const result = await apiCall(`/analyze/${requestId}`, 'GET', null, false);
                
                if (result.status === 'completed') {
                    addLog(`✅ Analysis completed for ${requestId}!`, 'info');
                    document.getElementById('results').textContent = JSON.stringify(result, null, 2);
                    document.getElementById('lastAnalysis').textContent = new Date().toLocaleTimeString();
                    
                    // Show summary
                    if (result.summary) {
                        addLog(`📊 Summary: ${result.summary}`, 'info');
                    }
                } else if (result.status === 'failed') {
                    addLog(`❌ Analysis failed for ${requestId}: ${result.error || 'Unknown error'}`, 'error');
                    document.getElementById('results').textContent = JSON.stringify(result, null, 2);
                } else if (result.status === 'not_found') {
                    addLog(`❌ Analysis ${requestId} not found`, 'error');
                } else {
                    // Still running, poll again
                    addLog(`⏳ Analysis still running... Status: ${result.status || 'unknown'}`, 'warning');
                    setTimeout(() => pollAnalysisResults(requestId), 2000);
                }
            }
            
            async function checkHealth() {
                addLog('💓 Checking system health...', 'info');
                const result = await apiCall('/health');
                document.getElementById('results').textContent = JSON.stringify(result, null, 2);
                
                if (result.status === 'healthy') {
                    addLog('✅ System is healthy', 'info');
                } else {
                    addLog('⚠️ System health issues detected', 'warning');
                }
            }
            
            async function sendChatMessage() {
                const message = document.getElementById('chatInput').value;
                if (!message.trim()) {
                    addLog('⚠️ Please enter a chat message', 'warning');
                    return;
                }
                
                addLog(`💬 Sending chat message: "${message}"`, 'info');
                const result = await apiCall('/chat', 'POST', { message });
                
                if (result.response) {
                    document.getElementById('chatResponse').innerHTML = `
                        <strong>🤖 Response:</strong><br>${result.response}<br>
                        <strong>💡 Suggestions:</strong> ${result.suggestions ? result.suggestions.join(', ') : 'None'}
                    `;
                    
                    addLog('✅ Chat response received', 'info');
                    
                    if (result.analysis_triggered) {
                        addLog(`🚀 Analysis triggered for: ${result.client_names.join(', ')}`, 'info');
                    }
                } else {
                    addLog('❌ No response from chat service', 'error');
                }
                
                // Clear input
                document.getElementById('chatInput').value = '';
            }
            
            // Initialize
            addLog('🚀 Windows Log Gathering Agent initialized', 'info');
            addLog('📡 Ready for commands', 'info');
            
            // Auto-refresh system status
            setInterval(async () => {
                try {
                    const health = await apiCall('/health', 'GET', null, false);
                    const llmStatusElement = document.getElementById('llmStatus');
                    
                    if (health.status === 'healthy') {
                        llmStatusElement.innerHTML = '<span class="status-indicator status-success"></span>Connected';
                    } else {
                        llmStatusElement.innerHTML = '<span class="status-indicator status-error"></span>Error';
                    }
                } catch (error) {
                    // Ignore silent health check errors
                }
            }, 10000); // Check every 10 seconds
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# Background task functions
async def run_analysis(request_id: str, client_names: List[str], include_summary: bool, force_refresh: bool):
    """Background task to run log analysis."""
    try:
        logger.info("=== BACKGROUND ANALYSIS STARTED ===", 
                   request_id=request_id, clients=client_names)
        
        # Step 1: Initialize cache entry with 'running' status
        analysis_cache[request_id] = {
            "request_id": request_id,
            "status": "running",
            "clients_analyzed": client_names,
            "timestamp": datetime.now(),
            "progress": "Starting analysis..."
        }
        logger.info("Step 1: Cache entry initialized", request_id=request_id)
        
        # Step 2: Collect logs
        logger.info("Step 2: Starting log collection", request_id=request_id)
        log_collections = await log_collector.collect_multiple_clients(client_names)
        logger.info("Step 2: Log collection completed", 
                   request_id=request_id, 
                   collections_count=len(log_collections))
        
        # Update cache with collection progress
        analysis_cache[request_id]["progress"] = "Log collection completed, starting LLM analysis..."
        
        # Step 3: Analyze logs
        logger.info("Step 3: Starting LLM analysis", request_id=request_id)
        analysis_results = await log_analyzer.analyze_multiple_clients(log_collections)
        logger.info("Step 3: LLM analysis completed", 
                   request_id=request_id,
                   analysis_count=len(analysis_results))
        
        # Step 4: Store results
        logger.info("Step 4: Storing analysis results", request_id=request_id)
        result_data = {
            "request_id": request_id,
            "status": "completed",
            "clients_analyzed": client_names,
            "results": [result.__dict__ for result in analysis_results],
            "timestamp": datetime.now()
        }
        
        if include_summary:
            logger.info("Step 4.1: Generating summary", request_id=request_id)
            result_data["summary"] = generate_multi_client_summary(analysis_results)
        
        # Cache results
        logger.info("Step 4.2: Caching main results", request_id=request_id)
        analysis_cache[request_id] = result_data
        
        # Also cache individual client results
        logger.info("Step 4.3: Caching individual client results", request_id=request_id)
        for result in analysis_results:
            analysis_cache[result.client_name] = {
                "client_name": result.client_name,
                "hostname": result.hostname,
                "overall_status": result.overall_status,
                "summary": result.summary,
                "action_items": result.action_items,
                "timestamp": result.timestamp,
                "log_analyses": [analysis.__dict__ for analysis in result.log_analyses]
            }
        
        logger.info("=== BACKGROUND ANALYSIS COMPLETED SUCCESSFULLY ===", 
                   request_id=request_id, 
                   clients_count=len(analysis_results),
                   cache_entries=len(analysis_cache))
        
    except Exception as e:
        logger.error("=== BACKGROUND ANALYSIS FAILED ===", 
                    request_id=request_id, 
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=str(e.__traceback__))
        
        # Store error result with detailed information
        analysis_cache[request_id] = {
            "request_id": request_id,
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__,
            "clients_analyzed": client_names,
            "timestamp": datetime.now()
        }
        
        # Also log current cache state for debugging
        logger.error("Current cache state after error", 
                    cache_keys=list(analysis_cache.keys()),
                    cache_size=len(analysis_cache))


async def process_chat_message(message: str, context: Optional[Dict], background_tasks: BackgroundTasks) -> ChatResponse:
    """Process chat message and return appropriate response."""
    message_lower = message.lower()
    
    # Analyze intent
    if any(word in message_lower for word in ["analyze", "check", "scan", "logs"]):
        # Extract client names if mentioned
        try:
            machines_config = settings.load_machines_config()
            mentioned_clients = []
            
            for client in machines_config.clients:
                if client.name.lower() in message_lower or client.hostname.lower() in message_lower:
                    mentioned_clients.append(client.name)
            
            if mentioned_clients:
                # Start analysis for mentioned clients
                request_id = f"chat_{int(datetime.now().timestamp())}"
                background_tasks.add_task(run_analysis, request_id, mentioned_clients, True, True)
                
                return ChatResponse(
                    response=f"I'm starting log analysis for {', '.join(mentioned_clients)}. This will take a few moments.",
                    suggestions=[
                        f"Check analysis results with: /analyze/{request_id}",
                        "List all clients: /clients",
                        "Ask about specific error types"
                    ],
                    analysis_triggered=True,
                    client_names=mentioned_clients
                )
            else:
                # General analysis request
                all_clients = [client.name for client in machines_config.clients]
                return ChatResponse(
                    response=f"I can analyze logs for these clients: {', '.join(all_clients)}. Which ones would you like me to check?",
                    suggestions=[
                        f"Analyze {all_clients[0]}",
                        "Analyze all clients", 
                        "Show client status"
                    ],
                    analysis_triggered=False
                )
        except Exception as e:
            return ChatResponse(
                response=f"I had trouble processing your analysis request: {str(e)}",
                suggestions=["List available clients", "Try a simpler request"],
                analysis_triggered=False
            )
    
    elif any(word in message_lower for word in ["status", "health", "list", "clients"]):
        # Status inquiry
        return ChatResponse(
            response="I can show you the status of all configured client machines. Would you like me to list them or check their current analysis status?",
            suggestions=[
                "List all clients",
                "Show client health status",
                "Analyze specific client"
            ],
            analysis_triggered=False
        )
    
    elif any(word in message_lower for word in ["help", "what can", "how do"]):
        # Help request
        return ChatResponse(
            response="I'm your Windows deployment log analysis assistant! I can:\n• Analyze SCCM and Windows Update logs\n• Check specific clients for issues\n• Provide troubleshooting recommendations\n• Show system status and health",
            suggestions=[
                "Analyze all clients",
                "List available clients", 
                "Check system health"
            ],
            analysis_triggered=False
        )
    
    else:
        # General response
        return ChatResponse(
            response="I can help you analyze Windows deployment logs and troubleshoot issues. What would you like me to check?",
            suggestions=[
                "Analyze client logs",
                "Show client status",
                "Get help"
            ],
            analysis_triggered=False
        )


def generate_multi_client_summary(results: List[ClientAnalysisResult]) -> str:
    """Generate summary for multiple client analysis."""
    total_clients = len(results)
    healthy_clients = len([r for r in results if r.overall_status == "healthy"])
    issue_clients = len([r for r in results if r.overall_status == "issues"])
    critical_clients = len([r for r in results if r.overall_status == "critical"])
    
    return f"Analysis Summary: {healthy_clients}/{total_clients} clients healthy, {issue_clients} with issues, {critical_clients} critical. Most common problems involve Windows Update and SCCM deployment failures."


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)