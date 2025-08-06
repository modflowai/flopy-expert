#!/usr/bin/env python3
"""
Logging configuration for the DSPy training pipeline

Provides consistent logging setup across all pipeline stages.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(name: str, level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Set up logging configuration
    
    Args:
        name: Logger name (usually module name)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to also log to file
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Console handler (simple format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (detailed format)
    if log_to_file:
        # Create logs directory
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"{name}_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)