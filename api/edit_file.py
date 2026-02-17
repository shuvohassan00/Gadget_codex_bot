#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
import os
import hashlib
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.utils import secure_filename
import uvicorn
from utils import LOGGER

edit_sessions = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    LOGGER.info("Starting FastAPI Edit File Server...")
    yield
    LOGGER.info("Shutting down FastAPI Edit File Server...")

app = FastAPI(lifespan=lifespan, title="Code Util Edit Server", version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key=os.urandom(32))

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_file_tree(path: Path, base_path: Path):
    items = []
    try:
        for item in sorted(path.iterdir()):
            if item.name.startswith('.'):
                continue
            
            relative_path = str(item.relative_to(base_path))
            
            if item.is_dir():
                items.append({
                    'name': item.name,
                    'type': 'folder',
                    'path': relative_path,
                    'children': get_file_tree(item, base_path)
                })
            else:
                items.append({
                    'name': item.name,
                    'type': 'file',
                    'path': relative_path,
                    'size': item.stat().st_size
                })
    except PermissionError:
        pass
    
    return items

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session: str = None):
    index_file = Path("templates/index.html")
    
    if not index_file.exists():
        return HTMLResponse(
            content="<h1>File Manager Not Configured</h1><p>Please create templates/index.html</p>",
            status_code=503
        )
    
    with open(index_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)

@app.post("/api/auth")
async def authenticate(request: Request):
    data = await request.json()
    session_id = data.get('session_id')
    username = data.get('username')
    password = data.get('password')
    
    LOGGER.info(f"Auth attempt for session: {session_id}")
    LOGGER.info(f"Available sessions: {list(edit_sessions.keys())}")
    
    if not session_id or session_id not in edit_sessions:
        LOGGER.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Invalid session")
    
    session_data = edit_sessions[session_id]
    password_hash = hash_password(password)
    
    if username == session_data['username'] and password_hash == session_data['password_hash']:
        request.session['authenticated'] = True
        request.session['session_id'] = session_id
        request.session['project_name'] = session_data['project_name']
        
        LOGGER.info(f"Authentication successful for session: {session_id}")
        
        return JSONResponse({
            'success': True,
            'project_name': session_data['project_name'],
            'owner_name': session_data['owner_name']
        })
    else:
        LOGGER.error(f"Invalid credentials for session: {session_id}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/session")
async def get_session_info(request: Request, session_id: str):
    LOGGER.info(f"Session info request for: {session_id}")
    LOGGER.info(f"Available sessions: {list(edit_sessions.keys())}")
    
    if not session_id or session_id not in edit_sessions:
        LOGGER.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Invalid session")
    
    session_data = edit_sessions[session_id]
    
    return JSONResponse({
        'project_name': session_data['project_name'],
        'owner_name': session_data['owner_name']
    })

@app.get("/api/check_auth")
async def check_auth(request: Request):
    if request.session.get('authenticated'):
        return JSONResponse({
            'authenticated': True,
            'session_id': request.session.get('session_id'),
            'project_name': request.session.get('project_name')
        })
    else:
        return JSONResponse({'authenticated': False})

@app.get("/api/files/tree")
async def get_tree(request: Request, session_id: str):
    if not session_id or session_id not in edit_sessions:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    if not request.session.get('authenticated') or request.session.get('session_id') != session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_data = edit_sessions[session_id]
    project_path = Path(session_data['project_path'])
    
    tree = get_file_tree(project_path, project_path)
    
    return JSONResponse({'tree': tree})

@app.get("/api/files/read")
async def read_file(request: Request, session_id: str, path: str):
    if not session_id or session_id not in edit_sessions:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    if not request.session.get('authenticated') or request.session.get('session_id') != session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_data = edit_sessions[session_id]
    project_path = Path(session_data['project_path'])
    
    full_path = project_path / path
    
    if not full_path.exists() or not full_path.is_relative_to(project_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return JSONResponse({
            'content': content,
            'path': path,
            'name': full_path.name
        })
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Binary file cannot be edited")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/write")
async def write_file(request: Request):
    data = await request.json()
    session_id = data.get('session_id')
    file_path = data.get('path')
    content = data.get('content')
    
    if not session_id or session_id not in edit_sessions:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    if not request.session.get('authenticated') or request.session.get('session_id') != session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_data = edit_sessions[session_id]
    project_path = Path(session_data['project_path'])
    
    full_path = project_path / file_path
    
    if not full_path.is_relative_to(project_path):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return JSONResponse({'success': True, 'message': 'File saved successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/download")
async def download_file(request: Request, session_id: str, path: str):
    if not session_id or session_id not in edit_sessions:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    if not request.session.get('authenticated') or request.session.get('session_id') != session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_data = edit_sessions[session_id]
    project_path = Path(session_data['project_path'])
    
    full_path = project_path / path
    
    if not full_path.exists() or not full_path.is_relative_to(project_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(full_path),
        filename=full_path.name,
        media_type='application/octet-stream'
    )

@app.post("/api/files/delete")
async def delete_file(request: Request):
    data = await request.json()
    session_id = data.get('session_id')
    file_path = data.get('path')
    
    if not session_id or session_id not in edit_sessions:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    if not request.session.get('authenticated') or request.session.get('session_id') != session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_data = edit_sessions[session_id]
    project_path = Path(session_data['project_path'])
    
    full_path = project_path / file_path
    
    if not full_path.exists() or not full_path.is_relative_to(project_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        if full_path.is_file():
            full_path.unlink()
        else:
            shutil.rmtree(full_path)
        
        return JSONResponse({'success': True, 'message': 'Deleted successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/create")
async def create_file(request: Request):
    data = await request.json()
    session_id = data.get('session_id')
    file_path = data.get('path')
    is_folder = data.get('is_folder', False)
    
    if not session_id or session_id not in edit_sessions:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    if not request.session.get('authenticated') or request.session.get('session_id') != session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_data = edit_sessions[session_id]
    project_path = Path(session_data['project_path'])
    
    full_path = project_path / file_path
    
    if not full_path.is_relative_to(project_path):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    try:
        if is_folder:
            full_path.mkdir(parents=True, exist_ok=True)
        else:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.touch()
        
        return JSONResponse({'success': True, 'message': 'Created successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/upload")
async def upload_file(
    request: Request,
    session_id: str = Form(...),
    path: str = Form(""),
    file: UploadFile = File(...)
):
    if not session_id or session_id not in edit_sessions:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    if not request.session.get('authenticated') or request.session.get('session_id') != session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_data = edit_sessions[session_id]
    project_path = Path(session_data['project_path'])
    
    filename = secure_filename(file.filename)
    
    if path:
        full_path = project_path / path / filename
    else:
        full_path = project_path / filename
    
    if not full_path.is_relative_to(project_path):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        return JSONResponse({'success': True, 'message': 'File uploaded successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/rename")
async def rename_file(request: Request):
    data = await request.json()
    session_id = data.get('session_id')
    old_path = data.get('old_path')
    new_name = data.get('new_name')
    
    if not session_id or session_id not in edit_sessions:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    if not request.session.get('authenticated') or request.session.get('session_id') != session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_data = edit_sessions[session_id]
    project_path = Path(session_data['project_path'])
    
    old_full_path = project_path / old_path
    new_full_path = old_full_path.parent / new_name
    
    if not old_full_path.exists() or not old_full_path.is_relative_to(project_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if not new_full_path.is_relative_to(project_path):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    try:
        old_full_path.rename(new_full_path)
        return JSONResponse({'success': True, 'message': 'Renamed successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({'success': True, 'message': 'Logged out successfully'})

async def run_server(host: str = "0.0.0.0", port: int = 8000):
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        loop="uvloop",
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_server())