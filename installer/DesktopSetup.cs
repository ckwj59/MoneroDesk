using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Windows.Forms;
using System.Diagnostics;
class DesktopSetup {
 [STAThread] static int Main(string[] args) {
  Application.EnableVisualStyles();
  bool extract=args.Length==2 && args[0]=="--extract-test";
  string dest=extract?Path.GetFullPath(args[1]):Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","XMR-CPU-GPU");
  if(!extract && MessageBox.Show("安装 XMR CPU + GPU（Windows x64）\n\n安装位置："+dest+"\n\n已验证：CPU、NVIDIA CUDA 矿池挖矿与 TLS 加密。\n暂不支持：AMD OpenCL、GPU 独挖、Linux。\nGPU 目前为实验实现，速度可能低于 CPU。\n程序不会自动开始挖矿。\n\n是否安装？","XMR 安装",MessageBoxButtons.OKCancel,MessageBoxIcon.Information)!=DialogResult.OK)return 0;
  try {
   foreach(string name in new string[]{"XMR","XMR-Engine"})foreach(var proc in Process.GetProcessesByName(name)) {
    try {if(proc.MainModule.FileName.StartsWith(dest+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new IOException("请先关闭该目录的 XMR，再安装。");}
    catch(System.ComponentModel.Win32Exception){}finally{proc.Dispose();}
   }
   Directory.CreateDirectory(dest);
   using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
   using(var archive=new ZipArchive(stream,ZipArchiveMode.Read))foreach(var item in archive.Entries) {
    string target=Path.GetFullPath(Path.Combine(dest,item.FullName));
    if(!target.StartsWith(Path.GetFullPath(dest)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new IOException("Invalid package path");
    if(item.Name.Length==0){Directory.CreateDirectory(target);continue;}
    Directory.CreateDirectory(Path.GetDirectoryName(target));
    using(var input=item.Open())using(var output=File.Create(target+".installing"))input.CopyTo(output);
    if(File.Exists(target))File.Delete(target);
    File.Move(target+".installing",target);
   }
   if(extract)return 0;
   dynamic shell=Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
   string shortcut=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"XMR CPU-GPU.lnk");
   dynamic link=shell.CreateShortcut(shortcut);
   link.TargetPath=Path.Combine(dest,"XMR.exe");link.WorkingDirectory=dest;link.IconLocation=Path.Combine(dest,"app.ico");link.Save();
   MessageBox.Show("安装完成。\n\n请双击桌面的 XMR CPU-GPU 打开。\n首次使用请填写自己的主收款地址。\n作者分配默认开启，可在界面取消。\n\n使用范围及卸载方法见安装目录的 使用说明.txt。","XMR",MessageBoxButtons.OK,MessageBoxIcon.Information);
   return 0;
  }catch(Exception ex){if(!extract)MessageBox.Show(ex.Message,"安装失败");else Console.Error.WriteLine(ex);return 1;}
 }
}
