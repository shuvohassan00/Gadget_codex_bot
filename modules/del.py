#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
import re
import shutil
import os
import psutil
from pathlib import Path
from telethon import events, Button
from bot import CodeUtilBot
import config
from utils import LOGGER

try:
    from modules.host import projects, project_processes
except ImportError:
    projects = {}
    project_processes = {}

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
del_pattern = re.compile(rf'^[{prefixes}]del$', re.IGNORECASE)

user_delete_sessions = {}

@CodeUtilBot.on(events.NewMessage(pattern=del_pattern))
async def delete_command_handler(event):
    user_id = event.sender_id
    
    LOGGER.info(f"User {user_id} requested project deletion")
    
    user_projects = {name: proj for name, proj in projects.items() if proj['owner_id'] == user_id}
    
    if not user_projects:
        await event.respond(
            "**📂 You don't have any projects yet!**\n\n"
            "**Use `/new` to create your first project.**"
        )
        raise events.StopPropagation
    
    buttons = []
    project_names = list(user_projects.keys())
    
    for i in range(0, len(project_names), 2):
        row = []
        row.append(Button.inline(f"🗑 {project_names[i]}", f"delselect_{project_names[i]}".encode()))
        if i + 1 < len(project_names):
            row.append(Button.inline(f"🗑 {project_names[i + 1]}", f"delselect_{project_names[i + 1]}".encode()))
        buttons.append(row)
    
    text = (
        f"**🗑 Select Project To Delete**\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**⚠️ Warning: This action cannot be undone!**\n"
        f"**Total Projects:** {len(user_projects)}\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Choose a project to delete:**"
    )
    
    await event.respond(text, buttons=buttons)
    raise events.StopPropagation

@CodeUtilBot.on(events.CallbackQuery(pattern=b"delselect_.*"))
async def delete_select_callback(event):
    data = event.data.decode()
    project_name = data[10:]
    user_id = event.sender_id
    
    if project_name not in projects:
        await event.answer("❌ Project not found!", alert=True)
        return
    
    project = projects[project_name]
    
    if project['owner_id'] != user_id:
        await event.answer("❌ You don't own this project!", alert=True)
        return
    
    LOGGER.info(f"User {user_id} confirming deletion of {project_name}")
    
    user_delete_sessions[user_id] = project_name
    
    text = (
        f"**⚠️ Confirm Project Deletion**\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Project Name:** {project_name}\n"
        f"**Project Size:** {project['size']}\n"
        f"**Status:** {project['status']}\n"
        f"**━━━━━━━━━━━━━**\n"
        f"**Are you sure you want to delete this project?**\n"
        f"**This action cannot be undone!**"
    )
    
    buttons = [
        [
            Button.inline("✅ Yes, Delete", f"delconfirm_{project_name}".encode()),
            Button.inline("❌ Cancel", b"delcancel")
        ]
    ]
    
    await event.edit(text, buttons=buttons)

@CodeUtilBot.on(events.CallbackQuery(pattern=b"delconfirm_.*"))
async def delete_confirm_callback(event):
    data = event.data.decode()
    project_name = data[11:]
    user_id = event.sender_id
    
    if project_name not in projects:
        await event.answer("❌ Project not found!", alert=True)
        return
    
    project = projects[project_name]
    
    if project['owner_id'] != user_id:
        await event.answer("❌ You don't own this project!", alert=True)
        return
    
    LOGGER.info(f"User {user_id} deleting project {project_name}")
    
    await event.answer("Deleting project...", alert=False)
    msg = await event.edit(f"**Deleting project `{project_name}`...**")
    
    try:
        if project['pid'] and psutil.pid_exists(project['pid']):
            try:
                process = project_processes.get(project_name)
                if process:
                    os.killpg(os.getpgid(process.pid), 9)
                else:
                    proc = psutil.Process(project['pid'])
                    proc.terminate()
                    proc.wait(timeout=5)
                
                if project_name in project_processes:
                    del project_processes[project_name]
                
                LOGGER.info(f"Stopped running process for {project_name}")
            except Exception as e:
                LOGGER.error(f"Error stopping process for {project_name}: {e}")
        
        project_path = Path(project['path'])
        if project_path.exists():
            shutil.rmtree(project_path)
            LOGGER.info(f"Deleted project directory for {project_name}")
        
        del projects[project_name]
        
        if user_id in user_delete_sessions:
            del user_delete_sessions[user_id]
        
        LOGGER.info(f"Project {project_name} deleted successfully by user {user_id}")
        
        await msg.edit(
            f"**✅ Project `{project_name}` Deleted Successfully!**\n\n"
            f"**All files and data have been removed.**"
        )
        
    except Exception as e:
        LOGGER.exception(f"Error deleting project {project_name}")
        await msg.edit(f"**❌ Error deleting project: {str(e)}**")

@CodeUtilBot.on(events.CallbackQuery(pattern=b"delcancel"))
async def delete_cancel_callback(event):
    user_id = event.sender_id
    
    if user_id in user_delete_sessions:
        project_name = user_delete_sessions[user_id]
        del user_delete_sessions[user_id]
        LOGGER.info(f"User {user_id} cancelled deletion of {project_name}")
    
    await event.edit("**❌ Deletion cancelled.**")