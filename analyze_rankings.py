#!/usr/bin/env python3
"""
Analyze scraped FantasyPros rankings
Provides insights and visualizations from the data
"""

import pandas as pd
from pathlib import Path
import argparse
from typing import List, Optional
import json


def load_latest_rankings(output_dir: Path = Path("output")) -> Optional[pd.DataFrame]:
    """Load the most recent rankings file"""
    csv_files = list(output_dir.glob("expert_rankings_*.csv"))
    if not csv_files:
        print("No ranking files found in output directory")
        return None
    
    # Get the most recent file
    latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    print(f"Loading rankings from: {latest_file.name}")
    
    return pd.read_csv(latest_file)


def show_top_consensus_players(df: pd.DataFrame, n: int = 20):
    """Show top N players by consensus ranking"""
    print(f"\n🏆 Top {n} Consensus Players:")
    print("=" * 80)
    
    top_players = df.nsmallest(n, 'Average Rank')[['Player', 'Average Rank', 'Std Dev', 'Expert Count']]
    
    for idx, row in top_players.iterrows():
        print(f"{int(row['Average Rank']):3d}. {row['Player']:<30} "
              f"(σ={row['Std Dev']:5.2f}, experts={int(row['Expert Count'])})")


def show_most_controversial_players(df: pd.DataFrame, n: int = 20, min_experts: int = 10):
    """Show players with highest standard deviation in rankings"""
    print(f"\n🔥 Top {n} Most Controversial Players (highest disagreement):")
    print("=" * 80)
    
    # Filter for players ranked by minimum number of experts
    filtered = df[df['Expert Count'] >= min_experts].copy()
    controversial = filtered.nlargest(n, 'Std Dev')[['Player', 'Average Rank', 'Std Dev', 'Expert Count']]
    
    for idx, row in controversial.iterrows():
        print(f"{row['Player']:<30} Avg: {row['Average Rank']:6.2f}, "
              f"StdDev: {row['Std Dev']:5.2f} (experts={int(row['Expert Count'])})")


def show_expert_statistics(df: pd.DataFrame):
    """Show statistics about the experts"""
    print("\n📊 Expert Statistics:")
    print("=" * 80)
    
    # Get expert columns
    expert_cols = [col for col in df.columns if col not in 
                   ['Player ID', 'Player', 'Average Rank', 'Std Dev', 'Expert Count']]
    
    print(f"Total experts analyzed: {len(expert_cols)}")
    
    # Show how many players each expert ranked
    expert_stats = []
    for expert in expert_cols:
        ranked_count = df[expert].notna().sum()
        avg_rank = df[expert].mean()
        expert_stats.append({
            'Expert': expert,
            'Players Ranked': ranked_count,
            'Average Rank Given': avg_rank
        })
    
    expert_df = pd.DataFrame(expert_stats).sort_values('Players Ranked', ascending=False)
    
    print("\nExperts by number of players ranked:")
    for idx, row in expert_df.head(10).iterrows():
        print(f"  {row['Expert']:<50} {int(row['Players Ranked']):>3} players")


def find_outlier_rankings(df: pd.DataFrame, player_name: str):
    """Find which experts are outliers for a specific player"""
    player_row = df[df['Player'] == player_name]
    
    if player_row.empty:
        print(f"\nPlayer '{player_name}' not found")
        return
    
    player_row = player_row.iloc[0]
    avg_rank = player_row['Average Rank']
    std_dev = player_row['Std Dev']
    
    print(f"\n🎯 Rankings for {player_name}:")
    print(f"Average Rank: {avg_rank:.1f} (±{std_dev:.1f})")
    print("=" * 80)
    
    # Get expert columns
    expert_cols = [col for col in df.columns if col not in 
                   ['Player ID', 'Player', 'Average Rank', 'Std Dev', 'Expert Count']]
    
    rankings = []
    for expert in expert_cols:
        rank = player_row[expert]
        if pd.notna(rank):
            deviation = rank - avg_rank
            rankings.append({
                'Expert': expert,
                'Rank': int(rank),
                'Deviation': deviation
            })
    
    # Sort by deviation
    rankings_df = pd.DataFrame(rankings).sort_values('Deviation')
    
    # Show highest and lowest rankings
    print("\nHighest rankings (most optimistic):")
    for idx, row in rankings_df.head(5).iterrows():
        print(f"  {row['Expert']:<50} Rank: {row['Rank']:>3} ({row['Deviation']:+.1f})")
    
    print("\nLowest rankings (most pessimistic):")
    for idx, row in rankings_df.tail(5).iterrows():
        print(f"  {row['Expert']:<50} Rank: {row['Rank']:>3} ({row['Deviation']:+.1f})")


def compare_position_groups(df: pd.DataFrame):
    """Analyze rankings by position (if position data is available)"""
    # This is a placeholder - would need position data in the CSV
    print("\n📍 Position Analysis:")
    print("=" * 80)
    print("Note: Position-specific analysis requires position data in the rankings.")
    print("Consider adding position information during scraping for deeper analysis.")


def export_consensus_rankings(df: pd.DataFrame, output_file: str = "consensus_rankings.txt"):
    """Export a clean consensus ranking list"""
    output_path = Path("output") / output_file
    
    with open(output_path, 'w') as f:
        f.write("FantasyPros Consensus Rankings\n")
        f.write("=" * 50 + "\n\n")
        
        for idx, row in df.iterrows():
            f.write(f"{int(row['Average Rank']):3d}. {row['Player']}\n")
    
    print(f"\n✅ Consensus rankings exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Analyze FantasyPros rankings data")
    parser.add_argument("--top", type=int, default=20, help="Number of top players to show")
    parser.add_argument("--player", type=str, help="Show detailed rankings for a specific player")
    parser.add_argument("--export", action="store_true", help="Export consensus rankings to text file")
    args = parser.parse_args()
    
    # Load the data
    df = load_latest_rankings()
    if df is None:
        return
    
    print(f"\n📊 Loaded {len(df)} players from {df['Expert Count'].iloc[0]} experts")
    
    # Run analyses
    show_top_consensus_players(df, n=args.top)
    show_most_controversial_players(df, n=args.top)
    show_expert_statistics(df)
    
    if args.player:
        find_outlier_rankings(df, args.player)
    
    if args.export:
        export_consensus_rankings(df)
    
    print("\n" + "=" * 80)
    print("Analysis complete! 🎉")


if __name__ == "__main__":
    main() 