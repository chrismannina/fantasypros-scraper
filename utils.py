"""
Utility functions for FantasyPros scraper
"""

import re
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path
import json


def clean_expert_name(name: str) -> str:
    """Clean and standardize expert name"""
    # Remove extra whitespace
    name = ' '.join(name.split())
    # Remove special characters that might cause issues
    name = re.sub(r'[^\w\s\(\)]', '', name)
    return name.strip()


def validate_rankings_data(rankings: Dict[str, float]) -> bool:
    """Validate that rankings data is reasonable"""
    if not rankings:
        return False
    
    values = list(rankings.values())
    
    # Check for reasonable ranking values (should be positive and not too large)
    if any(v < 0 or v > 1000 for v in values):
        return False
    
    return True


def merge_ranking_files(file_paths: List[Path], output_path: Path) -> pd.DataFrame:
    """Merge multiple ranking CSV files into one"""
    dfs = []
    
    for file_path in file_paths:
        if file_path.suffix == '.csv' and file_path.exists():
            df = pd.read_csv(file_path)
            dfs.append(df)
    
    if not dfs:
        raise ValueError("No valid CSV files found")
    
    # Merge on Player ID and Player columns
    merged_df = dfs[0]
    for df in dfs[1:]:
        # Get expert columns from new df
        expert_cols = [col for col in df.columns if col not in ['Player ID', 'Player', 'Average Rank', 'Std Dev', 'Expert Count']]
        cols_to_merge = ['Player ID', 'Player'] + expert_cols
        
        merged_df = pd.merge(
            merged_df, 
            df[cols_to_merge], 
            on=['Player ID', 'Player'], 
            how='outer'
        )
    
    # Recalculate statistics
    expert_columns = [col for col in merged_df.columns if col not in ['Player ID', 'Player', 'Average Rank', 'Std Dev', 'Expert Count']]
    merged_df['Average Rank'] = merged_df[expert_columns].mean(axis=1, skipna=True)
    merged_df['Std Dev'] = merged_df[expert_columns].std(axis=1, skipna=True)
    merged_df['Expert Count'] = merged_df[expert_columns].count(axis=1)
    
    # Sort by average rank
    merged_df = merged_df.sort_values('Average Rank')
    
    # Save merged file
    merged_df.to_csv(output_path, index=False)
    
    return merged_df


def find_ranking_differences(df: pd.DataFrame, expert1: str, expert2: str, threshold: int = 10) -> pd.DataFrame:
    """Find players with large ranking differences between two experts"""
    if expert1 not in df.columns or expert2 not in df.columns:
        raise ValueError(f"One or both experts not found in data")
    
    # Calculate difference
    df['Rank Difference'] = abs(df[expert1] - df[expert2])
    
    # Filter for large differences
    large_diffs = df[df['Rank Difference'] >= threshold].copy()
    
    # Sort by difference
    large_diffs = large_diffs.sort_values('Rank Difference', ascending=False)
    
    # Select relevant columns
    return large_diffs[['Player', expert1, expert2, 'Rank Difference', 'Average Rank']]


def export_expert_accuracy_report(rankings_file: Path, actual_results_file: Optional[Path] = None) -> Dict:
    """
    Generate expert accuracy report (if actual results are available)
    This is a placeholder for post-season analysis
    """
    df = pd.read_csv(rankings_file)
    
    report = {
        'total_experts': 0,
        'total_players': len(df),
        'expert_stats': {}
    }
    
    expert_columns = [col for col in df.columns if col not in ['Player ID', 'Player', 'Average Rank', 'Std Dev', 'Expert Count']]
    report['total_experts'] = len(expert_columns)
    
    for expert in expert_columns:
        expert_data = df[expert].dropna()
        report['expert_stats'][expert] = {
            'players_ranked': len(expert_data),
            'avg_rank': expert_data.mean(),
            'std_dev': expert_data.std()
        }
    
    return report


def load_saved_rankings(file_path: Path) -> pd.DataFrame:
    """Load previously saved rankings from CSV or JSON"""
    if file_path.suffix == '.csv':
        return pd.read_csv(file_path)
    elif file_path.suffix == '.json':
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Convert JSON to DataFrame
        df_data = []
        for player_id, rankings in data.items():
            row = {'Player ID': player_id}
            row.update(rankings)
            df_data.append(row)
        return pd.DataFrame(df_data)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")


if __name__ == "__main__":
    # Example usage
    print("FantasyPros Scraper Utilities")
    print("This module provides helper functions for the main scraper") 