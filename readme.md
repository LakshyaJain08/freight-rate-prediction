# Freight Rate Prediction Challenge

See `Freight_Rate_ML_Assessment.pdf` for the assessment instructions.

## What to do

1. Train and validate your model using `data/train_test.csv`.
2. Predict every load in `data/validation.csv`. Each load has a unique `load_id`.
3. Fill the matching `predicted_rate` values in `data/validation_predictions_template.csv` and save it as `validation_predictions.csv`.
4. Predict every row in `data/december_chart_inputs.csv` by filling its `predicted_rate` column.
5. Install the scorer requirements and run:

```bash
python -m pip install -r requirements.txt
python score.py --predictions validation_predictions.csv --december-predictions data/december_chart_inputs.csv
```

The scorer validates both files and creates `scorer_results/candidate_december.png`.

## Submit

- GitHub repository containing your code, dependencies, and run instructions
- `validation_predictions.csv`
- PDF or DOCX report containing your validation, data split approach and `candidate_december.png`
- 2-3 minute Loom link

## How to Run the Solution

1. **Install Dependencies:**
   Ensure you have Python installed, then install all required packages:
   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Option A — Run via Python Pipeline (CLI):**
   Run the end-to-end training, XAI generation, and prediction pipeline:
   ```bash
   python train_and_predict.py
   ```
   This will:
   - Perform time-based validation on October data.
   - Generate Explainable AI (XAI) feature importance and SHAP charts in `output/`.
   - Save predictions to `output/validation_predictions.csv` and `output/december-chart-inputs.csv`.

3. **Option B — Interactive Jupyter Notebook:**
   Launch Jupyter Notebook to explore the interactive EDA, model training, and SHAP visual explanations:
   ```bash
   jupyter notebook train_and_predict.ipynb
   ```

4. **Score and Validate:**
   Run the official scoring script to validate submission outputs and generate the candidate December chart:
   ```bash
   python score.py --predictions output/validation_predictions.csv --december-predictions output/december-chart-inputs.csv
   ```
   The chart will be created at `scorer_results/candidate_december.png`.

## Project Structure

```text
├── output/                        # Generated charts, predictions & XAI outputs
│   ├── eda_distribution.png       # Rate distribution histogram
│   ├── eda_equipment.png          # Boxplots by equipment type
│   ├── eda_distance.png           # Distance vs. Rate scatterplot
│   ├── xai_feature_importance.png # Tree Gain feature importance
│   ├── xai_shap_summary.png       # Global SHAP beeswarm summary
│   ├── xai_shap_waterfall.png     # Local prediction explanation for sample load
│   ├── validation_predictions.csv # Predicted rates for validation loads
│   └── december-chart-inputs.csv  # Completed December predictions
├── scorer_results/                # Output directory from score.py
│   └── candidate_december.png     # Final December prediction curve
├── train_and_predict.py           # Production Python pipeline script
├── train_and_predict.ipynb        # Interactive notebook with EDA & XAI
├── score.py                       # Assessment validation & scoring script
├── report.md                      # Comprehensive methodology & XAI report
├── report.docx                    # Formatted executive report document
├── requirements.txt               # Project dependencies
└── .gitignore                     # Git ignore rules
```

## Methodology Highlights

- **Time-Based Validation**: Data is chronologically partitioned (Train: Jan–Sep [43,147 loads], Validation: Oct [4,853 loads]) to strictly prevent lookahead leakage in time-series spot rate prediction.
- **Leakage-Free Imputation**: Outlier-resistant median imputer fit strictly on training data handles missing values and aligns the December inference schema.
- **XGBoost Categorical Partitioning**: Leverages `enable_categorical=True` to directly model 64 unique pickup/delivery hubs and equipment types without dimensionality explosion.
- **Explainable AI (XAI)**: Native C++ TreeSHAP integration provides global beeswarm feature impacts and load-level waterfall attribution.


