#!/usr/bin/env python3
"""
Setup script for FantasyPros Scraper
Helps users configure their environment
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil


def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   You have Python {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True


def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    print("📦 Creating virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create virtual environment")
        return False


def get_pip_command():
    """Get the appropriate pip command for the current OS"""
    if os.name == 'nt':  # Windows
        return os.path.join("venv", "Scripts", "pip")
    else:  # Unix/Linux/Mac
        return os.path.join("venv", "bin", "pip")


def get_python_command():
    """Get the appropriate python command for the current OS"""
    if os.name == 'nt':  # Windows
        return os.path.join("venv", "Scripts", "python")
    else:  # Unix/Linux/Mac
        return os.path.join("venv", "bin", "python")


def install_dependencies():
    """Install required dependencies"""
    pip_cmd = get_pip_command()
    
    print("📦 Installing dependencies...")
    try:
        # Upgrade pip first
        subprocess.run([pip_cmd, "install", "--upgrade", "pip"], check=True)
        
        # Install requirements
        subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed")
        
        # Install playwright browsers
        python_cmd = get_python_command()
        print("🌐 Installing Playwright browsers...")
        subprocess.run([python_cmd, "-m", "playwright", "install", "chromium"], check=True)
        print("✅ Playwright browsers installed")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_environment_file():
    """Create .env file from env.example if it doesn't exist"""
    env_path = Path(".env")
    env_example_path = Path("env.example")
    
    if env_path.exists():
        print("✅ .env file already exists")
        response = input("   Do you want to update it? (y/N): ").strip().lower()
        if response != 'y':
            return True
    
    if not env_example_path.exists():
        print("❌ env.example file not found")
        return False
    
    try:
        shutil.copy(env_example_path, env_path)
        print("✅ Created .env file from env.example")
        
        # Prompt for credentials
        print("\n🔐 Let's set up your FantasyPros credentials")
        email = input("   Enter your FantasyPros email: ").strip()
        password = input("   Enter your FantasyPros password: ").strip()
        
        if email and password:
            # Read the .env file
            with open(env_path, 'r') as f:
                content = f.read()
            
            # Replace placeholders
            content = content.replace('your_email@example.com', email)
            content = content.replace('your_password', password)
            
            # Write back
            with open(env_path, 'w') as f:
                f.write(content)
            
            print("✅ Credentials saved to .env file")
        else:
            print("⚠️  No credentials provided. Please edit .env manually")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False


def create_output_directory():
    """Create output directory if it doesn't exist"""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    print("✅ Output directory ready")
    return True


def main():
    """Main setup function"""
    print("🚀 FantasyPros Scraper Setup")
    print("=" * 40)
    
    steps = [
        ("Checking Python version", check_python_version),
        ("Creating virtual environment", create_virtual_environment),
        ("Installing dependencies", install_dependencies),
        ("Setting up environment file", setup_environment_file),
        ("Creating output directory", create_output_directory),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"\n❌ Setup failed at: {step_name}")
            sys.exit(1)
    
    print("\n" + "=" * 40)
    print("✅ Setup complete!")
    print("\nTo run the scraper:")
    
    if os.name == 'nt':  # Windows
        print("  1. Activate virtual environment: .\\venv\\Scripts\\activate")
        print("  2. Run the scraper: python scraper.py")
    else:  # Unix/Linux/Mac
        print("  1. Activate virtual environment: source venv/bin/activate")
        print("  2. Run the scraper: python scraper.py")
    
    print("\nFor more information, see README.md")


if __name__ == "__main__":
    main() 