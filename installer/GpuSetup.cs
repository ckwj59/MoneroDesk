using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Windows.Forms;
class GpuSetup {
 [STAThread] static void Main() {
  Application.EnableVisualStyles();
  string dest=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"MoneroDesk-GPU");
  if(MessageBox.Show("Install Monero Desk CPU + GPU to:\n"+dest+"\n\nIncludes CUDA plugin and runtime libraries. Your existing D:\\MoneroDesk installation will be kept. Mining only starts manually inside the app.","Monero Desk Setup",MessageBoxButtons.OKCancel)!=DialogResult.OK)return;
  try {
   foreach(var proc in System.Diagnostics.Process.GetProcessesByName("MoneroDesk")) {
    try { if(String.Equals(proc.MainModule.FileName,Path.Combine(dest,"MoneroDesk.exe"),StringComparison.OrdinalIgnoreCase)) { MessageBox.Show("Please close Monero Desk GPU, then run this installer again. Your settings will be preserved.","Monero Desk Setup");return; } }
    catch(System.ComponentModel.Win32Exception) { }
    finally { proc.Dispose(); }
   }
   Directory.CreateDirectory(dest);
   using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
   using(var zip=new ZipArchive(stream,ZipArchiveMode.Read)) {
    foreach(var item in zip.Entries) {
     string target=Path.GetFullPath(Path.Combine(dest,item.FullName));
     if(!target.StartsWith(Path.GetFullPath(dest)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("Invalid package path");
     if(item.Name.Length==0){Directory.CreateDirectory(target);continue;}
     Directory.CreateDirectory(Path.GetDirectoryName(target));
     using(var source=item.Open()) using(var output=File.Create(target))source.CopyTo(output);
    }
   }
   Type shellType=Type.GetTypeFromProgID("WScript.Shell");
   dynamic shell=Activator.CreateInstance(shellType);
   dynamic link=shell.CreateShortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"Monero Desk GPU.lnk"));
   link.TargetPath=Path.Combine(dest,"MoneroDesk.exe");link.WorkingDirectory=dest;link.IconLocation=Path.Combine(dest,"app.ico");link.Save();
   MessageBox.Show("Installed. Open the Monero Desk GPU shortcut. Enable CPU and select NVIDIA CUDA or AMD OpenCL in Mining settings. GPU is off by default. Display drivers are supplied by your hardware vendor.","Monero Desk Setup");
  }catch(Exception ex){MessageBox.Show("Installation failed: "+ex.Message,"Monero Desk Setup");Environment.ExitCode=1;}
 }
}
