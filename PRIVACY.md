# Privacy Notice

FL Lingo is a local desktop tool. It does not include telemetry or analytics.

## Local Data

FL Lingo stores user interface preferences, the last project path, language settings, translation rules, and optional translator settings using Qt `QSettings`. Depending on the operating system, these settings are stored in the user's normal application settings location.

Project files, translation exports, backups, and modified DLLs are written only to paths selected by the user or to project-specific output/backup locations.

## Update Checks

FL Lingo can check GitHub for the latest release. The automatic startup check can be disabled with:

```text
FLATLAS_DISABLE_STARTUP_UPDATE_CHECK=1
```

Manual update checks are started by the user from the application menu. Update checks contact GitHub and may reveal normal connection metadata such as IP address, user agent, and request time to GitHub.

## Automatic Translation

Automatic translation sends the selected source text to the configured translation provider. The built-in provider currently uses Google Translate through `deep-translator`. Separate helper scripts can use Google Cloud Translation or Google Gemini if the user installs those dependencies and supplies credentials.

Do not use automatic translation for text that you are not allowed to send to third-party services. Provider terms, privacy policies, quotas, and billing rules apply.

## API Keys

If an API key is entered in FL Lingo's translator settings, it is stored locally through `QSettings`. FL Lingo does not intentionally publish or upload stored API keys. Treat project files, exported logs, screenshots, and local settings backups as sensitive if they contain credentials or private text.

## No Account System

FL Lingo does not create user accounts and does not operate its own backend service.

