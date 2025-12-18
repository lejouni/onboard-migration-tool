"""
Test script to verify GitHub Enterprise configuration
"""
import os
import sys

def test_github_enterprise_config():
    """Test if GITHUB_API_URL is properly configured"""
    print("=" * 60)
    print("GitHub Enterprise Configuration Test")
    print("=" * 60)
    print()
    
    # Check environment variable
    github_api_url = os.getenv('GITHUB_API_URL')
    
    if github_api_url:
        print("✅ GITHUB_API_URL environment variable is set")
        print(f"   URL: {github_api_url}")
        
        # Validate URL format
        if not github_api_url.startswith('https://'):
            print("⚠️  Warning: URL should start with 'https://'")
        
        if not github_api_url.endswith('/api/v3'):
            print("⚠️  Warning: URL should end with '/api/v3' for GitHub Enterprise")
            
        print()
        print("Configuration appears valid for GitHub Enterprise Server")
        
    else:
        print("ℹ️  GITHUB_API_URL not set - using default GitHub.com")
        print("   Default URL: https://api.github.com")
        print()
        print("To configure GitHub Enterprise, set the environment variable:")
        print()
        print("   Windows PowerShell:")
        print('   $env:GITHUB_API_URL="https://github.enterprise.com/api/v3"')
        print()
        print("   Linux/Mac:")
        print('   export GITHUB_API_URL="https://github.enterprise.com/api/v3"')
    
    print()
    print("=" * 60)
    
    # Try to import GitHubService to verify configuration
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from github_service import GitHubService
        
        print("\n✅ GitHubService imported successfully")
        print(f"   BASE_URL: {GitHubService.BASE_URL}")
        
        if GitHubService.BASE_URL == 'https://api.github.com':
            print("   Target: GitHub.com (default)")
        else:
            print("   Target: GitHub Enterprise Server")
            
    except Exception as e:
        print(f"\n❌ Error importing GitHubService: {e}")
        print("   This is normal if database dependencies are not installed")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    test_github_enterprise_config()
