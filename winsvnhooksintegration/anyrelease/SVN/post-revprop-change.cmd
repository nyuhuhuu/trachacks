call D:\Trac\SVN\postRevPropChange.cmd "Test" "%1" "%2"
if %errorlevel% gtr 0 exit /B 1
exit /B 0