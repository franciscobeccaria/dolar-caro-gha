# Setting up GitHub Actions for Price Scraper

This document explains how to set up GitHub Actions to automatically run the price scraper on a daily basis and save the results to both the repository and Supabase.

## Workflow Overview

The GitHub Actions workflow is configured to:

1. Run automatically every day at 12:00 UTC (9:00 AM Argentina time)
2. Allow manual triggering via the GitHub Actions UI
3. Install all required dependencies
4. Run the price scraper
5. Commit and push any new data files to the repository

## Required Secrets

To run properly, the workflow needs the following secrets configured in your GitHub repository:

1. `SUPABASE_URL`: The URL of your Supabase instance
2. `SUPABASE_KEY`: The API key for your Supabase instance
3. `SUPABASE_SERVICE_ROLE`: The service role key for your Supabase instance (needed to bypass RLS)

## How to Add Secrets to Your GitHub Repository

1. Go to your GitHub repository
2. Click on "Settings" tab
3. In the left sidebar, click on "Secrets and variables" > "Actions"
4. Click on "New repository secret"
5. Add each of the required secrets:
   - Name: `SUPABASE_URL`
     Value: `https://kebhmvctgmtjzkyziggs.supabase.co` (or your Supabase URL)
   - Name: `SUPABASE_KEY`
     Value: Your Supabase API key
   - Name: `SUPABASE_SERVICE_ROLE`
     Value: Your Supabase service role key

## Troubleshooting

If the GitHub Actions workflow is failing, check the following:

1. **Missing Secrets**: Ensure all required secrets are properly configured
2. **Dependency Issues**: Check if all dependencies are correctly listed in requirements.txt
3. **Playwright Setup**: The workflow installs Playwright and Chromium, but if there are issues, you might need to adjust the installation steps
4. **File Permissions**: If the workflow can't commit changes, it might be a permissions issue

## Workflow File

The workflow is defined in `.github/workflows/price-scraper.yml`. You can modify this file to change the schedule, add more steps, or adjust the configuration as needed.

## Manual Triggering

To manually trigger the workflow:

1. Go to your GitHub repository
2. Click on the "Actions" tab
3. Select the "Price Scraper Workflow" from the list
4. Click on "Run workflow" button
5. Confirm by clicking "Run workflow" in the dropdown
