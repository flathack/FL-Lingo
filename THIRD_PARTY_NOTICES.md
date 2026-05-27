# Third-Party Notices

FL Lingo is licensed under the MIT License. See [LICENSE](LICENSE).

This file summarizes third-party software and services that FL Lingo uses or can interact with. It is provided for attribution and release packaging convenience; the upstream license texts and terms remain authoritative.

## Runtime Dependencies

| Component | Purpose | License / Terms |
|-----------|---------|-----------------|
| Python | Application runtime | Python Software Foundation License |
| PySide6 / Qt for Python | Desktop GUI framework | Qt for Python community packages are available under LGPLv3/GPLv3 or a commercial Qt license |
| pefile | Portable Executable and resource inspection | MIT License |
| deep-translator | Optional automatic translation provider integration | MIT License |

## Build And Development Dependencies

| Component | Purpose | License / Terms |
|-----------|---------|-----------------|
| PyInstaller | Windows executable packaging | GPL with PyInstaller bootloader exception |
| setuptools | Python packaging | MIT License |
| wheel | Python packaging | MIT License |
| pytest | Test runner | MIT License |
| pytest-qt | Qt test helpers | MIT License |
| Ruff | Linting | MIT License |

## Optional External Services

FL Lingo can send text to external translation services when the user starts automatic translation. The built-in provider currently uses Google Translate through `deep-translator`. Separate helper scripts can use Google Cloud Translation or Google Gemini when the user installs the required SDKs and provides credentials.

Use of these services is subject to the providers' own terms, privacy policies, quotas, and billing rules.

## Qt / PySide6 Distribution Note

Windows release builds bundle PySide6/Qt files through PyInstaller. If you redistribute FL Lingo binaries, make sure the release package includes this notice, the project license, and any license files shipped with the bundled Qt/PySide6 packages. If you need a proprietary distribution model that is incompatible with LGPL/GPL obligations, use an appropriate commercial Qt license.

