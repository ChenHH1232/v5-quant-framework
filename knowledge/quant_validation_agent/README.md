# Quant Validation Agent Knowledge Base

This folder stores reusable statistical validation knowledge for the Quant Validation Agent.

The Quant Validation Agent does not create financial theories and does not modify strategy logic. Its job is to test whether a research hypothesis has enough statistical evidence, whether the evidence is stable, and whether the result survives realistic data and validation constraints.

## Core Rule

Historical performance alone is never enough. A factor or strategy must show evidence that is:

- point-in-time;
- cross-sectionally or time-series statistically meaningful;
- robust across rolling windows and market states;
- not explained only by data leakage, sample choice, survivorship, or overfitting;
- reproducible from documented data and configuration.

## Folder Structure

- `methodology/`: validation methods and usage rules.
- `references/`: citation map for statistical and econometric methods.

