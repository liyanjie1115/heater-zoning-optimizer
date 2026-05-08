# Code Signing

This project supports Windows code signing, but a real signature requires:

1. A valid code-signing certificate in `.pfx` form or in the Windows certificate store
2. `signtool.exe` from the Windows SDK / App Certification Kit

## What is already prepared

- `scripts/sign_release.ps1`
  - Signs the desktop `exe`
  - Signs the installer `setup.exe`
  - Supports either:
    - `-PfxPath` and optional `-PfxPassword`
    - `-CertThumbprint`

## Example: sign with PFX

```powershell
.\scripts\sign_release.ps1 `
  -SigntoolExe "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe" `
  -PfxPath "D:\certs\codesign.pfx" `
  -PfxPassword "your-password"
```

## Example: sign with certificate store thumbprint

```powershell
.\scripts\sign_release.ps1 `
  -SigntoolExe "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe" `
  -CertThumbprint "YOUR_CERT_THUMBPRINT"
```

## Notes

- A self-signed certificate is only useful for internal testing.
- It does not remove the Windows "Unknown Publisher" warning for external users.
- To reduce SmartScreen / Unknown Publisher prompts for public distribution, use a trusted commercial code-signing certificate or Microsoft Trusted Signing.
