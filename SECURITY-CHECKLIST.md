# RailTwin-X Production Security Checklist & Operator Runbook

> **AUDIT MANDATE**: PS-26028 Grandmaster Remediation Protocol v1.0 (WO-08)  
> **SCOPE**: Credential Rotation, Historical Secret Purge, and Runtime Hardening  
> **APPLIES TO**: System Administrators, DevOps Engineers, and Security Officers

---

## ⚠️ Mandatory Notice: Human Operator Authority Required

Autonomous AI agents and CI/CD pipelines do **NOT** possess external administrative privileges to:
1. Log into external cloud identity providers (Google Cloud Console / Firebase Console).
2. Revoke and rotate service account credentials across live cloud tenants.
3. Perform destructive git history rewrites (`git filter-repo` / `git push --force --all`) on production remote repositories without organizational authorization.

The tasks outlined in **Section 1** and **Section 2** below **MUST be performed by a human operator** with appropriate cloud console and repository administrative privileges.

---

## Section 1: Google Cloud / Firebase Credential Revocation & Rotation

During historical development (specifically visible in commit `e3c4bfa` and archived references in commit `ead3099`), service account private keys (`firebase-admin.json`) and Firebase client API keys were tracked in source control.

Although `firebase-admin.json` is currently gitignored and local development uses decoupled SQLite/local state, any credentials that ever entered git history must be treated as permanently compromised until revoked in the cloud provider.

### Checklist for Human Administrator:

- [ ] **1.1 Identify Project & Service Account**
  - Navigate to [Google Cloud Console - IAM & Admin - Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts).
  - Select the project associated with the exposed service account (e.g. `farmer-4b216` or production project).
  - Locate the service account used for administrative access.

- [ ] **1.2 Revoke Compromised Keys Immediately**
  - Click on the service account email.
  - Navigate to the **Keys** tab.
  - Review all active keys and their creation dates.
  - Select **Delete** on all keys created on or before commit `e3c4bfa` (September 2026 or earlier).
  - Confirm deletion. Once deleted, any caller attempting to use the compromised `firebase-admin.json` will be rejected by Google IAM with `401 Unauthorized`.

- [ ] **1.3 Re-issue New Secret Key (If Cloud Firebase Is Needed)**
  - If external Firebase services are required in production:
    - Click **Add Key** -> **Create new key** -> **JSON**.
    - Store the downloaded JSON directly in a secure secrets manager (Google Secret Manager, HashiCorp Vault, or Kubernetes Secret).
    - **NEVER** save the key file inside the repository folder tree or check it into git.

- [ ] **1.4 Restrict Web API Key**
  - In [Google Cloud Console - APIs & Services - Credentials](https://console.cloud.google.com/apis/credentials):
  - Find the Browser/Web API key (`AIzaSy...`).
  - Configure **Application restrictions**:
    - Select **Websites** and add only authorized production domains (e.g., `https://railtwin.indianrailways.gov.in/*`).
  - Configure **API restrictions**:
    - Restrict key usage to only explicit APIs required by the client (e.g., Firebase Authentication, Cloud Firestore API).

---

## Section 2: Repository Git History Purge with `git-filter-repo`

Even though sensitive files (`firebase-admin.json`, `.env`, `web/.env`) are listed in `.gitignore` and deleted from the working tree, raw git objects remain in git's commit graph.

### Procedure for Repository Administrator:

- [ ] **2.1 Coordinate Repository Freeze**
  - Notify all engineers to commit and push all active branches.
  - Ensure local backups of the repository exist before running history rewriting.

- [ ] **2.2 Install `git-filter-repo`**
  ```bash
  pip install git-filter-repo
  ```

- [ ] **2.3 Clone Fresh Mirror**
  ```bash
  git clone --mirror https://github.com/organization/railtwin-x.git railtwin-mirror
  cd railtwin-mirror
  ```

- [ ] **2.4 Purge Compromised Files Across All Commits**
  ```bash
  git filter-repo --invert-paths \
    --path firebase-admin.json \
    --path .env \
    --path web/.env \
    --force
  ```

- [ ] **2.5 Redact Exposed Key Strings from Commit Diffs**
  Create an expressions file `expressions.txt`:
  ```
  AIzaSy…REDACTED==>REDACTED_HISTORICAL_KEY
  ```
  Execute string replacement:
  ```bash
  git filter-repo --replace-text expressions.txt --force
  ```

- [ ] **2.6 Force-Push Cleaned Graph to Remote**
  ```bash
  git push origin --force --all
  git push origin --force --tags
  ```

- [ ] **2.7 Instruct Team to Re-Clone**
  Engineers must delete existing local clones and clone fresh to avoid re-introducing pruned commits through merges.

---

## Section 3: JWT Secret Hardening & Runtime Verification

Production environments require an unpredictable, high-entropy secret key for HMAC-SHA256 token signing. The application fails fast on startup if an insecure or default secret is configured.

### Secret Key Rules:
- **Length**: Minimum 32 characters (256 bits recommended).
- **Entropy**: Cryptographically secure pseudo-random bytes.
- **Forbidden**: Cannot contain placeholder strings (`"insecure"`, `"development"`, `"changeme"`, `"secret"`, `"default"`, `"placeholder"`, `"dummy"`, `"example"`, `"replace-with"`).

### Setup Instructions:

- [ ] **3.1 Generate Secure Secret**
  Generate a 48-byte URL-safe base64 secret:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

- [ ] **3.2 Set Environment Variable**
  In production container deployment / systemd service / Kubernetes secret:
  ```bash
  export RAILTWIN_JWT_SECRET_KEY="<insert_generated_secret_here>"
  export RAILTWIN_ENV="production"
  ```

- [ ] **3.3 Verify Startup Gate**
  Verify that the application refuses to start if `RAILTWIN_JWT_SECRET_KEY` is omitted or weak:
  ```bash
  python -c "from config import Settings; s = Settings(ENV='production', JWT_SECRET_KEY='short')"
  # Expected: ValueError: RAILTWIN_JWT_SECRET_KEY must be a cryptographically secure secret...
  ```

---

## Section 4: Operational Verification Sign-Off

| Step | Description | Responsible Operator | Date Completed | Status |
|------|-------------|----------------------|----------------|--------|
| 1.0  | GCP Service Account Key Revocation | Cloud Admin | ______________ | [ ] PENDING |
| 2.0  | Web API Key Scope Restriction | Cloud Admin | ______________ | [ ] PENDING |
| 3.0  | Git History Purge (`git-filter-repo`) | Repo Admin | ______________ | [ ] PENDING |
| 4.0  | Production JWT Secret Configured | DevOps Lead | ______________ | [ ] PENDING |
| 5.0  | Zero Insecure Secrets in Container Images | DevOps Lead | ______________ | [ ] VERIFIED |
