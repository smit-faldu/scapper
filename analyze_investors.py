import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns

def clean_text(text):
    if pd.isna(text):
        return ""
    return str(text).strip()

def extract_investor_info(text):
    # Extract investor name, role, and firm
    name_pattern = r'([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)'
    match = re.search(name_pattern, text)
    if match:
        return {
            'name': match.group(1).strip(),
            'role': match.group(2).strip(),
            'firm': match.group(3).strip()
        }
    return None

def extract_investment_range(text):
    # Extract investment range
    range_pattern = r'\$([\d\.]+)K?\s*\(([\d\.]+)K?\s*-\s*([\d\.]+)K?\)'
    match = re.search(range_pattern, text)
    if match:
        return {
            'min': float(match.group(2)),
            'max': float(match.group(3))
        }
    return None

def extract_investment_categories(text):
    # Extract investment categories
    categories = []
    category_pattern = r'Investors in ([^,]+)'
    matches = re.finditer(category_pattern, text)
    for match in matches:
        category = match.group(1).strip()
        if category and not category.startswith('Investors in'):
            categories.append(category)
    return categories

def extract_locations(text):
    # Extract investment locations
    locations = []
    location_pattern = r'Investors in ([^,]+) \(([^)]+)\)'
    matches = re.finditer(location_pattern, text)
    for match in matches:
        location = f"{match.group(1)} ({match.group(2)})"
        locations.append(location)
    return locations

def analyze_investors():
    # Read the CSV file
    df = pd.read_csv('investor_data.csv')
    
    # Clean the text data
    df['all_text'] = df['all_text'].apply(clean_text)
    
    # Extract investor information
    investors = []
    for text in df['all_text']:
        if 'INVESTORS' in text:
            # Split the text into sections
            sections = text.split('Save View')
            for section in sections[1:]:  # Skip the first section as it's usually header
                investor_info = extract_investor_info(section)
                if investor_info:
                    investment_range = extract_investment_range(section)
                    if investment_range:
                        investor_info.update(investment_range)
                    
                    # Add investment categories and locations
                    investor_info['categories'] = extract_investment_categories(section)
                    investor_info['locations'] = extract_locations(section)
                    
                    investors.append(investor_info)
    
    # Convert to DataFrame
    investors_df = pd.DataFrame(investors)
    
    # Basic statistics
    print("\n=== Investor Analysis ===")
    print(f"Total number of investors: {len(investors_df)}")
    
    if not investors_df.empty:
        # Role distribution
        role_counts = investors_df['role'].value_counts()
        print("\nRole Distribution:")
        print(role_counts)
        
        # Investment range statistics
        if 'min' in investors_df.columns and 'max' in investors_df.columns:
            print("\nInvestment Range Statistics:")
            print(f"Average minimum investment: ${investors_df['min'].mean():.2f}K")
            print(f"Average maximum investment: ${investors_df['max'].mean():.2f}K")
        
        # Top firms
        firm_counts = investors_df['firm'].value_counts().head(10)
        print("\nTop 10 Investment Firms:")
        print(firm_counts)
        
        # Investment categories analysis
        all_categories = []
        for categories in investors_df['categories']:
            all_categories.extend(categories)
        
        category_counts = Counter(all_categories)
        print("\nTop 10 Investment Categories:")
        for category, count in category_counts.most_common(10):
            print(f"{category}: {count}")
        
        # Location analysis
        all_locations = []
        for locations in investors_df['locations']:
            all_locations.extend(locations)
        
        location_counts = Counter(all_locations)
        print("\nTop 10 Investment Locations:")
        for location, count in location_counts.most_common(10):
            print(f"{location}: {count}")
        
        # Create visualizations
        plt.figure(figsize=(12, 6))
        sns.countplot(data=investors_df, y='role', order=role_counts.index)
        plt.title('Distribution of Investor Roles')
        plt.tight_layout()
        plt.savefig('investor_roles.png')
        
        if 'min' in investors_df.columns and 'max' in investors_df.columns:
            plt.figure(figsize=(10, 6))
            sns.boxplot(data=investors_df[['min', 'max']])
            plt.title('Investment Range Distribution')
            plt.ylabel('Amount (K)')
            plt.tight_layout()
            plt.savefig('investment_ranges.png')
        
        # Create category distribution plot
        plt.figure(figsize=(15, 8))
        top_categories = dict(category_counts.most_common(15))
        plt.barh(list(top_categories.keys()), list(top_categories.values()))
        plt.title('Top 15 Investment Categories')
        plt.xlabel('Number of Investors')
        plt.tight_layout()
        plt.savefig('investment_categories.png')

if __name__ == "__main__":
    analyze_investors() 