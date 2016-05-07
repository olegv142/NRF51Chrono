;--------------------------------
; NSIS installer script
;--------------------------------

!define TITLE        "Kronoz wireless timer system"
!define COMPANY      "Nobody Cares, Inc."
!define PROD_NAME    "Kronoz"
!define PFOLDER      "${PROD_NAME}"
!define PRODUCT      "${PROD_NAME}"
!define YEARS        "2016"
!define VERSION      "0.7.0.0"

!define UNINSTALL_NAME "${TITLE} software"

!define PYTHON_VERSION "3.5"

!define FTDI_DRIVER "CDM21216_Setup.exe"

SetCompressor /SOLID lzma

BrandingText "${COMPANY}"
Name    "${PROD_NAME}"
OutFile "${PROD_NAME}_${VERSION}.exe"

VIProductVersion "${VERSION}"

VIAddVersionKey "ProductName" "${PRODUCT}"
VIAddVersionKey "CompanyName" "${COMPANY}"
VIAddVersionKey "FileDescription" "${PRODUCT} installer"
VIAddVersionKey "LegalCopyright" "(C) ${COMPANY} ${YEARS}"
VIAddVersionKey "FileVersion" "${VERSION}"

; Request application privileges for Windows Vista
RequestExecutionLevel admin

; The default installation directory
InstallDir $PROGRAMFILES\${PROD_NAME}

; Registry key to check for directory (so if you install again, it will 
; overwrite the old one automatically)
InstallDirRegKey HKLM "Software\${PROD_NAME}" "Install_Dir"

Icon kronoz.ico

!include "LogicLib.nsh"
!include "winmessages.nsh"

var /GLOBAL PyPath

Function .onInit
  ReadRegStr $PyPath HKLM "Software\Python\PythonCore\${PYTHON_VERSION}\InstallPath" ""
  ${If} $PyPath == ""
    ReadRegStr $PyPath HKCU "Software\Python\PythonCore\${PYTHON_VERSION}\InstallPath" ""
  ${EndIf}
  ${If} $PyPath == ""
    MessageBox MB_OK "Python ${PYTHON_VERSION} is not found. Please install Anaconda distribution first."
    Abort
  ${EndIf}
FunctionEnd

;--------------------------------
; Pages

; Install init
Section "-init"
  ; Install for current user
  SetShellVarContext current

  ; Create uninstaller
  SetOutPath $INSTDIR

  File kronoz.py
  File form.ui
  File lane.ui
  File kronoz.ico
  File driver\${FTDI_DRIVER}
  
  ExecWait "$INSTDIR\${FTDI_DRIVER}"
  Delete   "$INSTDIR\${FTDI_DRIVER}"

  ExecWait "$PyPath\Scripts\pip.exe install pyserial"

  ; Create start menu
  CreateDirectory "$SMPROGRAMS\${PFOLDER}"
  CreateShortCut "$SMPROGRAMS\${PFOLDER}\${PROD_NAME}.lnk" "$PyPath\pythonw.exe" '"$INSTDIR\kronoz.py"' "$INSTDIR\kronoz.ico"
  ; Create desktop shortcut
  CreateShortCut "$DESKTOP\${PROD_NAME}.lnk" "$PyPath\pythonw.exe" '"$INSTDIR\kronoz.py"' "$INSTDIR\kronoz.ico"

  ; Create uninstaller
  WriteUninstaller "uninstall.exe"

  ; Write the installation path into the registry
  WriteRegStr HKLM Software\${PROD_NAME} "Install_Dir" "$INSTDIR"

  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROD_NAME}" "DisplayName" "${UNINSTALL_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROD_NAME}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROD_NAME}" "Publisher" "${COMPANY}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROD_NAME}" "DisplayIcon" $INSTDIR\kronoz.ico
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROD_NAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROD_NAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROD_NAME}" "NoRepair" 1

SectionEnd

;--------------------------------

; Uninstaller

Section "Uninstall"
  ; Uninsall for all users
  SetShellVarContext current

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROD_NAME}"
  DeleteRegKey HKLM "Software\${PROD_NAME}"

  ; Remove shortcuts, if any
  Delete "$DESKTOP\${PROD_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${PFOLDER}"

  ; Remove directories used
  RMDir /r "$SMPROGRAMS\${PFOLDER}"
  RMDir /r "$INSTDIR"

SectionEnd
