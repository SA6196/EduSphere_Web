# Publish the EduSphere repository to GitHub

The downloadable ZIP is a source snapshot, not a Git repository with commit history. Extract it, review `.gitignore`, and confirm no local `.env`, generated demo-account SQL, tokens or private student records have been added.

1. In GitHub, create a new **private** repository named `EduSphere-LMS` without selecting 'Add README' (this package contains one).
2. Open PowerShell at the extracted `EduSphere-LMS/` root.
3. Create a commit and push to your own remote:

```powershell
git init
git branch -M main
git add .
git status --short     # review carefully: no .env, credentials, venv, node_modules
git commit -m 'Initial tested EduSphere LMS repository'
git remote add origin https://github.com/YOUR_ACCOUNT/EduSphere-LMS.git
git push -u origin main
```

Use your GitHub username/organization in the remote URL; do not paste a personal-access token into a shell command. Git Credential Manager or SSH can authenticate securely. If using an existing repository, follow its existing branch/remote policies instead of reinitializing. Enable branch protection and dependency alerts. No open-source license is included; obtain all project owners' agreement before changing repository visibility or choosing a license.

The `.github/workflows/ci.yml` workflow checks source and frontend code without Oracle credentials. It does **not** run the destructive opt-in scripts in `qa/manual_acceptance`. Configure deployment credentials through a protected environment, not committed files.
