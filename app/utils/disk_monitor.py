"""
System utilities for disk space monitoring and model cleanup.
"""
import os
import shutil
import psutil
from pathlib import Path
from typing import Dict, List
import logging


class DiskSpaceMonitor:
    """Monitor disk space and manage model cleanup"""
    
    LOW_DISK_THRESHOLD = 15  # percent
    
    @staticmethod
    def get_disk_usage() -> Dict[str, float]:
        """Get current disk usage statistics"""
        try:
            usage = psutil.disk_usage('/')
            return {
                'total_gb': usage.total / (1024 ** 3),
                'used_gb': usage.used / (1024 ** 3),
                'free_gb': usage.free / (1024 ** 3),
                'percent_used': usage.percent,
                'percent_free': 100 - usage.percent,
                'is_low': (100 - usage.percent) < DiskSpaceMonitor.LOW_DISK_THRESHOLD
            }
        except Exception as e:
            logging.error(f"Error getting disk usage: {e}")
            return {
                'error': str(e),
                'is_low': False
            }
    
    @staticmethod
    def get_model_directory_size() -> Dict[str, float]:
        """Get size of saved models directory"""
        model_dir = Path('model/saved_models')
        
        if not model_dir.exists():
            return {'total_mb': 0, 'model_count': 0}
        
        total_size = 0
        model_count = 0
        
        for path in model_dir.rglob('*'):
            if path.is_file():
                total_size += path.stat().st_size
                if path.name == 'model.h5':
                    model_count += 1
        
        return {
            'total_mb': total_size / (1024 ** 2),
            'total_gb': total_size / (1024 ** 3),
            'model_count': model_count
        }
    
    @staticmethod
    def list_saved_models() -> List[Dict]:
        """List all saved models with their sizes and dates"""
        model_dir = Path('model/saved_models')
        
        if not model_dir.exists():
            return []
        
        models = []
        for model_folder in model_dir.iterdir():
            if model_folder.is_dir():
                model_file = model_folder / 'model.h5'
                if model_file.exists():
                    stat = model_file.stat()
                    models.append({
                        'path': str(model_folder),
                        'name': model_folder.name,
                        'size_mb': stat.st_size / (1024 ** 2),
                        'modified': stat.st_mtime,
                        'model_file': str(model_file)
                    })
        
        # Sort by modified time (oldest first)
        models.sort(key=lambda x: x['modified'])
        return models
    
    @staticmethod
    def cleanup_old_models(keep_newest: int = 2) -> Dict[str, any]:
        """
        Clean up old models, keeping only the newest N models per stock.
        
        Args:
            keep_newest: Number of newest models to keep per stock symbol
            
        Returns:
            Dict with cleanup statistics
        """
        model_dir = Path('model/saved_models')
        
        if not model_dir.exists():
            return {'deleted': 0, 'space_freed_mb': 0}
        
        # Group models by stock symbol
        models_by_symbol = {}
        for model_folder in model_dir.iterdir():
            if model_folder.is_dir():
                # Extract symbol from folder name (format: SYMBOL_modeltype_timestamp)
                parts = model_folder.name.split('_')
                if len(parts) >= 2:
                    symbol = parts[0]
                    if symbol not in models_by_symbol:
                        models_by_symbol[symbol] = []
                    
                    model_file = model_folder / 'model.h5'
                    if model_file.exists():
                        models_by_symbol[symbol].append({
                            'folder': model_folder,
                            'modified': model_file.stat().st_mtime
                        })
        
        deleted_count = 0
        space_freed = 0
        
        # For each symbol, keep only the newest N models
        for symbol, models in models_by_symbol.items():
            # Sort by modification time (newest first)
            models.sort(key=lambda x: x['modified'], reverse=True)
            
            # Delete old models
            for model_info in models[keep_newest:]:
                folder = model_info['folder']
                try:
                    # Calculate folder size before deletion
                    folder_size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
                    
                    # Delete the folder
                    shutil.rmtree(folder)
                    
                    deleted_count += 1
                    space_freed += folder_size
                    logging.info(f"Deleted old model: {folder.name}")
                    
                except Exception as e:
                    logging.error(f"Error deleting model folder {folder}: {e}")
        
        return {
            'deleted': deleted_count,
            'space_freed_mb': space_freed / (1024 ** 2),
            'space_freed_gb': space_freed / (1024 ** 3)
        }
    
    @staticmethod
    def auto_cleanup_if_low_space() -> Dict[str, any]:
        """Automatically cleanup models if disk space is low"""
        disk_usage = DiskSpaceMonitor.get_disk_usage()
        
        if disk_usage.get('is_low', False):
            logging.warning(f"Low disk space detected: {disk_usage.get('percent_free', 0):.2f}% free")
            return DiskSpaceMonitor.cleanup_old_models(keep_newest=1)
        
        return {'cleanup_needed': False}
