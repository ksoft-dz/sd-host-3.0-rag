# How to Get a Claude API Key

Follow these steps to get your Claude API key from Anthropic:

## Step 1: Create an Anthropic Account

1. Go to: **https://console.anthropic.com/**
2. Click **"Sign Up"** (or "Sign In" if you already have an account)
3. Create an account using:
   - Email + Password, OR
   - Google account, OR
   - GitHub account

## Step 2: Access API Keys

1. Once logged in, go to: **https://console.anthropic.com/settings/keys**
2. Or navigate: **Settings** → **API Keys** (from the left sidebar)

## Step 3: Create a New API Key

1. Click **"Create Key"** button
2. Give your key a descriptive name (e.g., "RAG Project - SD Host")
3. Click **"Create Key"**
4. **IMPORTANT:** Copy the API key immediately - you won't be able to see it again!
   - Format: `sk-ant-api03-...` (starts with `sk-ant-`)

## Step 4: Add Credits to Your Account

Before you can use the API, you need to add credits:

1. Go to: **https://console.anthropic.com/settings/billing**
2. Click **"Add Credits"** or **"Purchase Credits"**
3. Choose your credit amount:
   - Minimum: $5 USD
   - Recommended for this project: $10-20 USD (should be plenty for 83 figures)
4. Enter payment information and complete purchase

### Pricing (as of 2024):
- **Claude 3.5 Haiku** (used in our script - most cost-effective):
  - Input: ~$0.80 per 1M tokens
  - Output: ~$4.00 per 1M tokens
  - With images: ~$0.80 per 1M input tokens
  
- **Estimated cost for 83 figures:**
  - Generation: ~$0.50 - $2.00
  - Validation: ~$0.30 - $1.00
  - **Total: ~$1-3 USD** (very rough estimate)

## Step 5: Set the API Key in Your Environment

### On Windows (PowerShell):
```powershell
# Temporary (current session only)
$env:ANTHROPIC_API_KEY = "sk-ant-api03-YOUR-KEY-HERE"

# Permanent (add to PowerShell profile)
# 1. Edit profile:
notepad $PROFILE

# 2. Add this line:
$env:ANTHROPIC_API_KEY = "sk-ant-api03-YOUR-KEY-HERE"

# 3. Save and reload:
. $PROFILE
```

### On Linux/Mac (bash/zsh):
```bash
# Temporary (current session only)
export ANTHROPIC_API_KEY="sk-ant-api03-YOUR-KEY-HERE"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-YOUR-KEY-HERE"' >> ~/.bashrc
source ~/.bashrc
```

### Verify It's Set:
```powershell
# PowerShell
echo $env:ANTHROPIC_API_KEY

# Linux/Mac
echo $ANTHROPIC_API_KEY
```

## Step 6: Install Required Python Library

```powershell
pip install anthropic
```

## Step 7: Test the Script

```powershell
# Process a single figure first (test)
python figures/convert_figures_to_plantuml.py --figure FIG_1_1

# If successful, process all figures
python figures/convert_figures_to_plantuml.py

# Or skip already processed ones
python figures/convert_figures_to_plantuml.py --skip-existing
```

## Important Notes

⚠️ **Security:**
- Never commit your API key to git
- Never share your API key publicly
- Treat it like a password

💰 **Cost Management:**
- Start with a small test (1-2 figures) to estimate costs
- Monitor your usage: https://console.anthropic.com/settings/billing
- Set up usage alerts in the console

📊 **Usage Tracking:**
- Check your dashboard: https://console.anthropic.com/settings/usage
- The script logs token usage for each figure in `conversion.log`

## Troubleshooting

**"Invalid API Key" Error:**
- Check you copied the entire key (starts with `sk-ant-`)
- Verify the environment variable is set: `echo $env:ANTHROPIC_API_KEY`
- Make sure there are no extra spaces or quotes

**"Insufficient Credits" Error:**
- Add more credits in the billing section
- Check your balance: https://console.anthropic.com/settings/billing

**Rate Limit Errors:**
- Free tier may have lower limits
- Wait a few minutes between large batches
- Consider upgrading to paid tier for higher limits

## Alternative: Use API Key File (More Secure)

Instead of environment variables, you can create a `.env` file:

```bash
# Create .env file in project root
echo "ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE" > .env

# Add .env to .gitignore
echo ".env" >> .gitignore
```

Then modify the script to load from `.env` using `python-dotenv`:
```bash
pip install python-dotenv
```

## Questions?

- API Documentation: https://docs.anthropic.com/
- Support: https://support.anthropic.com/
- Community: https://discord.gg/anthropic
