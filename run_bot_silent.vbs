Set WshShell = CreateObject("WScript.Shell")
' Dapatkan direktori tempat script VBScript ini berada secara dinamis
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
' Ubah working directory ke direktori script ini
WshShell.CurrentDirectory = strPath
' Jalankan run_bot.bat secara tidak terlihat (0) melalui cmd /c
WshShell.Run "cmd /c " & Chr(34) & strPath & "\run_bot.bat" & Chr(34), 0, False
Set WshShell = Nothing
