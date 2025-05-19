import argparse
import os
import json
import logging
from dotenv import set_key

def update_config(config_key, config_value):
    """Update a configuration value in .env file"""
    env_path = os.path.join(os.getcwd(), '.env')
    
    # Create .env file if it doesn't exist
    if not os.path.exists(env_path):
        open(env_path, 'a').close()
        
    set_key(env_path, config_key, config_value)
    print(f"Updated {config_key} to {config_value}")

def show_config():
    """Display current configuration values"""
    from config import (
        API_KEY, STORAGE_TYPE, DUCKDB_PATH, POSTGRES_URI,
        DATA_SOURCE, LOG_LEVEL, LOG_FILE, WATCH_FOLDER, BATCH_SIZE
    )
    
    # Mask API key for security
    masked_api_key = f"{API_KEY[:3]}..." if API_KEY and len(API_KEY) > 3 else "[Not Set]"
    
    config = {
        "API_KEY": masked_api_key,
        "STORAGE_TYPE": STORAGE_TYPE,
        "DUCKDB_PATH": DUCKDB_PATH,
        "POSTGRES_URI": POSTGRES_URI,
        "DATA_SOURCE": DATA_SOURCE,
        "LOG_LEVEL": LOG_LEVEL,
        "LOG_FILE": LOG_FILE,
        "WATCH_FOLDER": WATCH_FOLDER,
        "BATCH_SIZE": BATCH_SIZE
    }
    
    print(json.dumps(config, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Admin tool for Paper Extractor")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration commands")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    
    # Show config
    config_subparsers.add_parser("show", help="Show current configuration")
    
    # Set config
    set_config = config_subparsers.add_parser("set", help="Set a configuration value")
    set_config.add_argument("key", choices=[
        "API_KEY", "STORAGE_TYPE", "DUCKDB_PATH", "POSTGRES_URI",
        "DATA_SOURCE", "LOG_LEVEL", "LOG_FILE", "WATCH_FOLDER", "BATCH_SIZE"
    ])
    set_config.add_argument("value", help="Value to set")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    if args.command == "config":
        if not args.config_command:
            config_parser.print_help()
            return
            
        if args.config_command == "show":
            show_config()
        elif args.config_command == "set":
            update_config(args.key, args.value)

if __name__ == "__main__":
    main()