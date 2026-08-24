from typing import Tuple, List
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt

def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads the historical training, validation, and December evaluation datasets.
    
    Returns:
        Tuple containing (train_df, val_df, dec_df) as pandas DataFrames.
    """
    train_df = pd.read_csv('train-test.csv')
    val_df = pd.read_csv('validation.csv')
    dec_df = pd.read_csv('december-chart-inputs.csv')
    return train_df, val_df, dec_df

def engineer_features(df: pd.DataFrame, is_december: bool = False) -> pd.DataFrame:
    """
    Applies feature engineering transformations to freight data.
    
    Extracts temporal components (month, day of week, day of month),
    casts categorical columns for native tree partitioning, and
    generates placeholder NaN columns for December inference.
    
    Args:
        df: Input freight dataframe.
        is_december: Flag indicating if the dataset is the December inference partition.
        
    Returns:
        Transformed DataFrame with engineered feature columns.
    """
    df = df.copy()
    
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_month'] = df['date'].dt.day
    
    if is_december:
        for col in ['market_index', 'quote_signal', 'pickup_lat', 'pickup_lon', 'delivery_lat', 'delivery_lon']:
            df[col] = np.nan
            
    cat_cols = ['pickup', 'delivery', 'equipment']
    for col in cat_cols:
        df[col] = df[col].astype('category')
        
    return df

def main():
    print("Loading data...")
    train_df, val_df, dec_df = load_data()
    
    print("Engineering features...")
    train_df = engineer_features(train_df)
    val_df = engineer_features(val_df)
    dec_df_feat = engineer_features(dec_df, is_december=True)
    
    features = [
        'pickup', 'delivery', 'distance', 'equipment', 'weight',
        'market_index', 'quote_signal', 
        'month', 'day_of_week', 'day_of_month',
        'pickup_lat', 'pickup_lon', 'delivery_lat', 'delivery_lon'
    ]
    target = 'posted_rate'
    
    num_cols = ['weight', 'market_index', 'quote_signal', 'pickup_lat', 'pickup_lon', 'delivery_lat', 'delivery_lon']
    
    imputer = SimpleImputer(strategy='median')
    imputer.fit(train_df[num_cols])
    
    train_df[num_cols] = imputer.transform(train_df[num_cols])
    val_df[num_cols] = imputer.transform(val_df[num_cols])
    dec_df_feat[num_cols] = imputer.transform(dec_df_feat[num_cols])
    
    print("Setting up validation split...")
    
    train_split = train_df[train_df['date'] < '2025-10-01']
    val_split = train_df[train_df['date'] >= '2025-10-01']
    
    X_train_split = train_split[features]
    y_train_split = train_split[target]
    
    X_val_split = val_split[features]
    y_val_split = val_split[target]
    
    print(f"Training on {len(train_split)} rows, validating on {len(val_split)} rows...")
    
    # Configure XGBoost regressor with robust regularization parameters
    model = xgb.XGBRegressor(
        n_estimators=300,        # 300 boosting rounds for convergence
        learning_rate=0.05,      # Conservative step size shrinkage
        max_depth=6,             # 6 levels of interaction depth
        subsample=0.8,           # 80% row subsampling per tree (stochastic boosting)
        colsample_bytree=0.8,    # 80% feature subsampling per split
        enable_categorical=True, # Native experimental categorical partitioning
        random_state=42          # Deterministic seed for reproducibility
    )
    
    model.fit(
        X_train_split, 
        y_train_split,
        eval_set=[(X_val_split, y_val_split)],
        verbose=50
    )
    
    val_preds = model.predict(X_val_split)
    rmse = np.sqrt(mean_squared_error(y_val_split, val_preds))
    mae = mean_absolute_error(y_val_split, val_preds)
    print(f"Validation RMSE: {rmse:.2f}")
    print(f"Validation MAE: {mae:.2f}")
    
    import os
    os.makedirs('output', exist_ok=True)
    
    # ---------------------------------------------------------
    # Explainable AI (XAI) Section
    # ---------------------------------------------------------
    print("Generating Explainable AI (XAI) insights...")
    try:
        import matplotlib.pyplot as plt
        import shap
        
        # 1. Built-in Feature Importance (Gain)
        importance = model.get_booster().get_score(importance_type='gain')
        importance_df = pd.DataFrame({
            'Feature': list(importance.keys()),
            'Gain': list(importance.values())
        }).sort_values(by='Gain', ascending=True)
        
        plt.figure(figsize=(10, 6))
        plt.barh(importance_df['Feature'], importance_df['Gain'], color='#2b5c8f')
        plt.title('XAI: Global Feature Importance (Gain Metric)', fontsize=14, pad=12)
        plt.xlabel('Average Gain (Improvement to Model Accuracy)', fontsize=11)
        plt.tight_layout()
        plt.savefig('output/xai_feature_importance.png', dpi=300)
        plt.close()
        print("Saved output/xai_feature_importance.png")
        
        # 2. SHAP Global Summary (Beeswarm) using native XGBoost TreeSHAP
        sample_val = X_val_split.sample(n=min(1000, len(X_val_split)), random_state=42)
        dmat_sample = xgb.DMatrix(sample_val, enable_categorical=True)
        contribs = model.get_booster().predict(dmat_sample, pred_contribs=True)
        
        shap_values = contribs[:, :-1]
        base_values = contribs[:, -1]
        
        shap_explanation = shap.Explanation(
            values=shap_values,
            base_values=base_values,
            data=sample_val,
            feature_names=features
        )
        
        plt.figure(figsize=(10, 6))
        shap.summary_plot(shap_values, sample_val, show=False)
        plt.title('XAI: SHAP Global Feature Impact (Directional Summary)', fontsize=14, pad=12)
        plt.tight_layout()
        plt.savefig('output/xai_shap_summary.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("Saved output/xai_shap_summary.png")
        
        # 3. SHAP Local Explanation (Waterfall Plot for Sample Load)
        plt.figure(figsize=(10, 6))
        shap.plots.waterfall(shap_explanation[0], show=False)
        plt.title('XAI: SHAP Local Prediction Breakdown (Individual Load)', fontsize=14, pad=12)
        plt.tight_layout()
        plt.savefig('output/xai_shap_waterfall.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("Saved output/xai_shap_waterfall.png")
        
    except Exception as e:
        print(f"Note: XAI generation encountered an exception: {e}")

    print("Retraining on full training data...")
    X_train_full = train_df[features]
    y_train_full = train_df[target]
    
    model_full = xgb.XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        enable_categorical=True,
        random_state=42
    )
    model_full.fit(X_train_full, y_train_full)
    
    print("Predicting on final validation data...")
    X_val = val_df[features]
    final_val_preds = model_full.predict(X_val)
    
    val_out = val_df[['load_id']].copy()
    val_out['predicted_rate'] = final_val_preds
    val_out.to_csv('output/validation_predictions.csv', index=False)
    print("Saved output/validation_predictions.csv")
    
    print("Predicting on December chart inputs...")
    X_dec = dec_df_feat[features]
    dec_preds = model_full.predict(X_dec)
    
    dec_out = dec_df.copy()
    dec_out['predicted_rate'] = dec_preds
    dec_out.to_csv('output/december-chart-inputs.csv', index=False)
    print("Saved output/december-chart-inputs.csv")
    
    print("Pipeline complete!")

if __name__ == "__main__":
    main()
