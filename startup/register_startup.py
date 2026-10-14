"""
SPIDER — Windows Startup Registration
Registers SPIDER to run on Windows login using Task Scheduler.
Run this once as Administrator.
"""
import subprocess
import sys
from pathlib import Path


def register_startup():
    """Register SPIDER as a Windows startup task."""
    spider_main = Path(__file__).parent.parent / "main.py"
    python_exe = sys.executable

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{spider_main}"</Arguments>
      <WorkingDirectory>{spider_main.parent}</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <Priority>7</Priority>
  </Settings>
  <RegistrationInfo>
    <Description>SPIDER Personal AI Assistant - Auto-start on login</Description>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>"""

    xml_path = Path(__file__).parent / "spider_task.xml"
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(task_xml)

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", "SPIDER_Startup", "/XML", str(xml_path), "/F"],
        capture_output=True, text=True,
    )

    if result.returncode == 0:
        print("✅ SPIDER registered to start on Windows login!")
        print("   Task name: SPIDER_Startup")
        print("   To remove: schtasks /Delete /TN SPIDER_Startup /F")
    else:
        print(f"❌ Failed to register startup task: {result.stderr}")
        print("   Try running as Administrator.")

    xml_path.unlink(missing_ok=True)


if __name__ == "__main__":
    register_startup()
