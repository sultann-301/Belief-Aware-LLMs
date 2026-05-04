#!/usr/bin/env python
# coding: utf-8

# # Belief-Aware LLMs Evaluation Analysis
# This notebook provides extensive visualizations of the `eval_results.csv` data.
# It focuses on the single-agent runs, comparing models across different contexts (With Store, Store History, No Store), domains, and prompt versions.
# 

# In[1]:


import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set visual style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


# ## Data Loading and Transformation

# In[2]:


# Load the data
df = pd.read_csv('eval_results.csv')

# Clean up legacy entries where Model might be 'unknown'
df = df[df['Model'] != 'unknown']

# We are primarily interested in 'Average_Accuracy' for these comparisons
df_acc = df[df['Summary_Metric'] == 'Average_Accuracy'].copy()

# Melt the dataframe to make the context types (With_Store, Store_History, No_Store) a single categorical column
# This makes it much easier to plot with seaborn
id_vars = ['Timestamp', 'Domain', 'Model', 'Temp', 'Prompt_Ver', 'Runs']
value_vars = ['With_Store', 'Store_History', 'No_Store']

df_melted = pd.melt(df_acc, id_vars=id_vars, value_vars=value_vars, 
                    var_name='Context_Type', value_name='Accuracy')

# Clean up Accuracy values - handle cases like '0.7900p'
df_melted['Accuracy'] = df_melted['Accuracy'].astype(str).str.replace(r'[^0-9.]', '', regex=True)
df_melted['Accuracy'] = pd.to_numeric(df_melted['Accuracy'], errors='coerce')
df_melted = df_melted.dropna(subset=['Accuracy'])

df_melted.head()


# ## 1. Overall Context Condition Impact
# How much does providing the Belief Store or History help?

# In[3]:


plt.figure(figsize=(10, 6))
sns.barplot(data=df_melted, x='Context_Type', y='Accuracy', capsize=.1, errorbar='ci')
plt.title('Overall Average Accuracy by Context Type', fontsize=16)
plt.ylabel('Average Accuracy')
plt.xlabel('Context Condition')
plt.ylim(0, 1.05)
plt.show()


# ## 2. Model Breakdown
# Which models are best at utilizing the Belief Store without hallucinating?

# In[4]:


plt.figure(figsize=(14, 7))
sns.barplot(data=df_melted, x='Model', y='Accuracy', hue='Context_Type', capsize=.05, errorbar='ci')
plt.title('Model Performance Across Context Types', fontsize=16)
plt.ylabel('Average Accuracy')
plt.xlabel('Model')
plt.xticks(rotation=45)
plt.legend(title='Context Condition')
plt.ylim(0, 1.05)
plt.tight_layout()
plt.show()


# ## 3. High-Level Domain Analysis
# Performance broken down by the exact scenario string from the CSV.

# In[5]:


plt.figure(figsize=(14, 7))
sns.barplot(data=df_melted, x='Domain', y='Accuracy', hue='Context_Type', capsize=.05, errorbar='ci')
plt.title('Performance Across Evaluation Domains/Scenarios', fontsize=16)
plt.ylabel('Average Accuracy')
plt.xlabel('Domain & Scenario')
plt.xticks(rotation=45, ha='right')
plt.legend(title='Context Condition')
plt.ylim(0, 1.05)
plt.tight_layout()
plt.show()


# ## 4. Feature Extraction: Base Domain vs Scenario Type
# To get clearer insights, we split the string `loan_negation` into Base Domain (`loan`) and Scenario (`negation`).

# In[6]:


# Extract Base Domain and Scenario Type for deeper analysis
def extract_base_domain(domain):
    for base in ['loan', 'alien_clinic', 'crime_scene', 'thorncrester']:
        if domain.startswith(base):
            return base
    return 'other'

def extract_scenario(domain):
    for scenario in ['_belief_maintenance', '_negation', '_absurd_temporal', '_grounding']:
        if domain.endswith(scenario):
            return scenario.lstrip('_')
    return 'base'

df_melted['Base_Domain'] = df_melted['Domain'].apply(extract_base_domain)
df_melted['Scenario'] = df_melted['Domain'].apply(extract_scenario)

df_melted[['Domain', 'Base_Domain', 'Scenario']].head()


# In[7]:


plt.figure(figsize=(12, 6))
sns.barplot(data=df_melted, x='Base_Domain', y='Accuracy', hue='Context_Type', capsize=.05, errorbar='ci')
plt.title('Performance by Base Domain', fontsize=16)
plt.ylabel('Average Accuracy')
plt.xlabel('Base Domain')
plt.legend(title='Context Condition')
plt.ylim(0, 1.05)
plt.tight_layout()
plt.show()


# In[8]:


plt.figure(figsize=(12, 6))
sns.barplot(data=df_melted, x='Scenario', y='Accuracy', hue='Context_Type', capsize=.05, errorbar='ci')
plt.title('Performance by Scenario Type', fontsize=16)
plt.ylabel('Average Accuracy')
plt.xlabel('Scenario Type')
plt.legend(title='Context Condition')
plt.ylim(0, 1.05)
plt.tight_layout()
plt.show()


# ## 5. Prompt Engineering Impact
# Comparing prompt iterations (e.g., v5 vs v13).

# In[9]:


plt.figure(figsize=(10, 6))
sns.barplot(data=df_melted, x='Prompt_Ver', y='Accuracy', hue='Context_Type', capsize=.05, errorbar='ci')
plt.title('Impact of Prompt Version on Accuracy', fontsize=16)
plt.ylabel('Average Accuracy')
plt.xlabel('Prompt Version')
plt.legend(title='Context Condition')
plt.ylim(0, 1.05)
plt.tight_layout()
plt.show()


# ## 6. Per-Model Performance Across Base Domains
# Comparing how different models perform on each specific domain when using the Belief Store.

# In[10]:


# Filter for 'With_Store' context to see how models perform across domains when given the store
df_with_store = df_melted[df_melted['Context_Type'] == 'With_Store']

plt.figure(figsize=(14, 7))
sns.barplot(data=df_with_store, x='Base_Domain', y='Accuracy', hue='Model', capsize=.05, errorbar='ci')
plt.title('Per-Model Performance Across Base Domains (With Store)', fontsize=16)
plt.ylabel('Average Accuracy')
plt.xlabel('Base Domain')
plt.legend(title='Model')
plt.ylim(0, 1.05)
plt.tight_layout()
plt.show()

