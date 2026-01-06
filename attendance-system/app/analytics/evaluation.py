import pandas as pd
import numpy as np
from app.utils.logging import setup_logger


class AttendanceEvaluation:
    """
    Computes biometric evaluation metrics (FAR, FRR, Accuracy).
    Enterprise-grade evaluation framework for MSc-level analysis.
    """

    def __init__(self):
        self.logger = setup_logger()

    def get_genuine_impostor_split(self, df: pd.DataFrame):
        """
        Split attendance data into genuine and impostor attempts.
        
        Args:
            df: DataFrame with attendance records (must have 'face_verified' and 'recognition_score')
            
        Returns:
            Tuple of (genuine_df, impostor_df)
        """
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        if 'face_verified' not in df.columns:
            self.logger.warning("'face_verified' column not found. Cannot split genuine/impostor.")
            return pd.DataFrame(), pd.DataFrame()
        
        # Genuine: face_verified == 1 (successful face recognition)
        # Impostor: face_verified == 0 (face mismatch or failed recognition)
        genuine = df[df['face_verified'] == 1].copy()
        impostor = df[df['face_verified'] == 0].copy()
        
        self.logger.info(f"Split data: {len(genuine)} genuine attempts, {len(impostor)} impostor attempts")
        
        return genuine, impostor

    def compute_metrics(self, df: pd.DataFrame, threshold: float = 0.5, use_stored_decision: bool = True):
        """
        Compute FAR, FRR, and Accuracy at a given threshold.
        
        Args:
            df: DataFrame with attendance records
            threshold: Similarity score threshold (0.0 to 1.0) - used only if use_stored_decision=False
            use_stored_decision: If True, use stored system_decision and threshold_used (recommended)
            
        Returns:
            Dictionary with threshold, FAR, FRR, Accuracy, and counts
        """
        if df.empty:
            return {
                "threshold": threshold,
                "FAR": 0.0,
                "FRR": 0.0,
                "accuracy": 0.0,
                "total_attempts": 0,
                "genuine_attempts": 0,
                "impostor_attempts": 0,
                "false_accepts": 0,
                "false_rejects": 0,
                "true_accepts": 0,
                "true_rejects": 0
            }
        
        # Validate threshold
        threshold = max(0.0, min(1.0, threshold))
        
        # Split into genuine and impostor
        genuine, impostor = self.get_genuine_impostor_split(df)
        
        total_attempts = len(df)
        genuine_count = len(genuine)
        impostor_count = len(impostor)
        
        # Use stored system_decision if available (recommended for accurate evaluation)
        if use_stored_decision and 'system_decision' in df.columns and 'threshold_used' in df.columns:
            # Use stored decisions - this is the correct way for evaluation
            # Ground truth: face_verified (1=genuine, 0=impostor)
            # System decision: accept or reject (stored in system_decision)
            
            # Normalize system_decision to lowercase for comparison
            df['system_decision_lower'] = df['system_decision'].astype(str).str.lower().str.strip()
            
            # Genuine attempts
            if genuine_count > 0:
                genuine_df = df[df['face_verified'] == 1]
                # False Rejects: Genuine attempts that were rejected
                false_rejects = len(genuine_df[genuine_df['system_decision_lower'] == 'reject'])
                # True Accepts: Genuine attempts that were accepted
                true_accepts = genuine_count - false_rejects
                FRR = false_rejects / genuine_count if genuine_count > 0 else 0.0
            else:
                false_rejects = 0
                true_accepts = 0
                FRR = 0.0
            
            # Impostor attempts
            if impostor_count > 0:
                impostor_df = df[df['face_verified'] == 0]
                # False Accepts: Impostor attempts that were accepted
                false_accepts = len(impostor_df[impostor_df['system_decision_lower'] == 'accept'])
                # True Rejects: Impostor attempts that were rejected
                true_rejects = impostor_count - false_accepts
                FAR = false_accepts / impostor_count if impostor_count > 0 else 0.0
            else:
                false_accepts = 0
                true_rejects = 0
                FAR = 0.0
            
            # Use the most common threshold_used (or provided threshold as fallback)
            if 'threshold_used' in df.columns:
                threshold_used = df['threshold_used'].mode()
                if len(threshold_used) > 0:
                    threshold = float(threshold_used.iloc[0])
                else:
                    threshold = df['threshold_used'].median()
                    if pd.isna(threshold):
                        threshold = threshold  # Use provided threshold
        else:
            # Fallback: Use score-based evaluation (for backward compatibility)
            if 'recognition_score' not in df.columns:
                self.logger.error("'recognition_score' column not found and use_stored_decision=False")
                return {
                    "threshold": threshold,
                    "FAR": 0.0,
                    "FRR": 0.0,
                    "accuracy": 0.0,
                    "total_attempts": total_attempts,
                    "genuine_attempts": genuine_count,
                    "impostor_attempts": impostor_count,
                    "false_accepts": 0,
                    "false_rejects": 0,
                    "true_accepts": 0,
                    "true_rejects": 0
                }
            
            # Compute metrics using score comparison
            if genuine_count > 0:
                # False Rejects: Genuine attempts with score below threshold
                false_rejects = len(genuine[genuine['recognition_score'] < threshold])
                # True Accepts: Genuine attempts with score >= threshold
                true_accepts = genuine_count - false_rejects
                FRR = false_rejects / genuine_count
            else:
                false_rejects = 0
                true_accepts = 0
                FRR = 0.0
            
            if impostor_count > 0:
                # False Accepts: Impostor attempts with score >= threshold
                false_accepts = len(impostor[impostor['recognition_score'] >= threshold])
                # True Rejects: Impostor attempts with score < threshold
                true_rejects = impostor_count - false_accepts
                FAR = false_accepts / impostor_count
            else:
                false_accepts = 0
                true_rejects = 0
                FAR = 0.0
        
        # Accuracy: (True Positives + True Negatives) / Total
        if total_attempts > 0:
            accuracy = (true_accepts + true_rejects) / total_attempts
        else:
            accuracy = 0.0
        
        return {
            "threshold": threshold,
            "FAR": round(FAR, 4),
            "FRR": round(FRR, 4),
            "accuracy": round(accuracy, 4),
            "total_attempts": total_attempts,
            "genuine_attempts": genuine_count,
            "impostor_attempts": impostor_count,
            "false_accepts": false_accepts,
            "false_rejects": false_rejects,
            "true_accepts": true_accepts,
            "true_rejects": true_rejects
        }

    def compute_metrics_sweep(self, df: pd.DataFrame, num_thresholds: int = 50):
        """
        Compute FAR and FRR across a range of thresholds.
        
        Args:
            df: DataFrame with attendance records
            num_thresholds: Number of threshold points to evaluate (default: 50)
            
        Returns:
            DataFrame with columns: threshold, FAR, FRR, accuracy
        """
        if df.empty:
            return pd.DataFrame(columns=['threshold', 'FAR', 'FRR', 'accuracy'])
        
        thresholds = np.linspace(0.0, 1.0, num_thresholds)
        results = []
        
        for threshold in thresholds:
            metrics = self.compute_metrics(df, threshold)
            results.append({
                'threshold': threshold,
                'FAR': metrics['FAR'],
                'FRR': metrics['FRR'],
                'accuracy': metrics['accuracy']
            })
        
        return pd.DataFrame(results)

    def find_eer_threshold(self, df: pd.DataFrame, num_thresholds: int = 100):
        """
        Find the Equal Error Rate (EER) threshold where FAR = FRR.
        
        Args:
            df: DataFrame with attendance records
            num_thresholds: Number of threshold points to evaluate
            
        Returns:
            Dictionary with EER threshold, EER value, and metrics at that threshold
        """
        if df.empty:
            return {
                "eer_threshold": 0.5,
                "eer_value": 0.0,
                "FAR_at_eer": 0.0,
                "FRR_at_eer": 0.0
            }
        
        sweep_df = self.compute_metrics_sweep(df, num_thresholds)
        
        if sweep_df.empty:
            return {
                "eer_threshold": 0.5,
                "eer_value": 0.0,
                "FAR_at_eer": 0.0,
                "FRR_at_eer": 0.0
            }
        
        # Find threshold where FAR and FRR are closest
        sweep_df['far_frr_diff'] = abs(sweep_df['FAR'] - sweep_df['FRR'])
        eer_row = sweep_df.loc[sweep_df['far_frr_diff'].idxmin()]
        
        eer_threshold = eer_row['threshold']
        eer_value = (eer_row['FAR'] + eer_row['FRR']) / 2
        
        return {
            "eer_threshold": round(eer_threshold, 4),
            "eer_value": round(eer_value, 4),
            "FAR_at_eer": round(eer_row['FAR'], 4),
            "FRR_at_eer": round(eer_row['FRR'], 4)
        }

    def get_score_statistics(self, df: pd.DataFrame):
        """
        Get statistical summary of recognition scores for genuine and impostor attempts.
        
        Args:
            df: DataFrame with attendance records
            
        Returns:
            Dictionary with statistics for genuine and impostor scores
        """
        if df.empty or 'recognition_score' not in df.columns:
            return {
                "genuine": {},
                "impostor": {}
            }
        
        genuine, impostor = self.get_genuine_impostor_split(df)
        
        genuine_stats = {}
        impostor_stats = {}
        
        if len(genuine) > 0 and 'recognition_score' in genuine.columns:
            genuine_scores = genuine['recognition_score'].dropna()
            if len(genuine_scores) > 0:
                genuine_stats = {
                    "count": len(genuine_scores),
                    "mean": round(genuine_scores.mean(), 4),
                    "median": round(genuine_scores.median(), 4),
                    "std": round(genuine_scores.std(), 4),
                    "min": round(genuine_scores.min(), 4),
                    "max": round(genuine_scores.max(), 4),
                    "q25": round(genuine_scores.quantile(0.25), 4),
                    "q75": round(genuine_scores.quantile(0.75), 4)
                }
        
        if len(impostor) > 0 and 'recognition_score' in impostor.columns:
            impostor_scores = impostor['recognition_score'].dropna()
            if len(impostor_scores) > 0:
                impostor_stats = {
                    "count": len(impostor_scores),
                    "mean": round(impostor_scores.mean(), 4),
                    "median": round(impostor_scores.median(), 4),
                    "std": round(impostor_scores.std(), 4),
                    "min": round(impostor_scores.min(), 4),
                    "max": round(impostor_scores.max(), 4),
                    "q25": round(impostor_scores.quantile(0.25), 4),
                    "q75": round(impostor_scores.quantile(0.75), 4)
                }
        
        return {
            "genuine": genuine_stats,
            "impostor": impostor_stats
        }

    def validate_outcomes(self, df: pd.DataFrame):
        """
        Validate the 4 outcomes (True Accept, False Reject, False Accept, True Reject)
        using stored threshold and system_decision.
        
        Args:
            df: DataFrame with attendance records (must have threshold_used, system_decision, face_verified)
            
        Returns:
            DataFrame with outcome column added
        """
        if df.empty:
            return df
        
        required_cols = ['threshold_used', 'system_decision', 'face_verified']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            self.logger.warning(f"Cannot validate outcomes: missing columns {missing_cols}")
            # Fallback: compute from score if threshold_used is available
            if 'threshold_used' in df.columns and 'recognition_score' in df.columns:
                from app.config.settings import SIMILARITY_THRESHOLD
                df['threshold_used'] = df['threshold_used'].fillna(SIMILARITY_THRESHOLD)
                df['system_decision'] = df.apply(
                    lambda row: 'accept' if pd.notna(row['recognition_score']) and row['recognition_score'] >= row['threshold_used'] else 'reject',
                    axis=1
                )
            else:
                return df
        
        df = df.copy()
        
        # Ground truth: genuine (1) or impostor (0)
        df['ground_truth'] = df['face_verified'].map({1: 'genuine', 0: 'impostor'})
        
        # System decision: accept or reject (normalize to lowercase)
        if 'system_decision' in df.columns:
            df['system_decision_lower'] = df['system_decision'].astype(str).str.lower()
        else:
            # Compute from score if not available
            from app.config.settings import SIMILARITY_THRESHOLD
            threshold = df['threshold_used'].fillna(SIMILARITY_THRESHOLD) if 'threshold_used' in df.columns else SIMILARITY_THRESHOLD
            df['system_decision_lower'] = df.apply(
                lambda row: 'accept' if pd.notna(row['recognition_score']) and row['recognition_score'] >= threshold else 'reject',
                axis=1
            )
        
        # Validate outcomes
        conditions = [
            (df['ground_truth'] == 'genuine') & (df['system_decision_lower'] == 'accept'),
            (df['ground_truth'] == 'genuine') & (df['system_decision_lower'] == 'reject'),
            (df['ground_truth'] == 'impostor') & (df['system_decision_lower'] == 'accept'),
            (df['ground_truth'] == 'impostor') & (df['system_decision_lower'] == 'reject')
        ]
        
        outcomes = ['true_accept', 'false_reject', 'false_accept', 'true_reject']
        df['outcome'] = np.select(conditions, outcomes, default='unknown')
        
        return df

    def get_outcome_counts(self, df: pd.DataFrame):
        """
        Get counts for each outcome type.
        
        Args:
            df: DataFrame with validated outcomes (will validate if needed)
            
        Returns:
            Dictionary with outcome counts
        """
        if df.empty:
            return {
                'true_accept': 0,
                'false_reject': 0,
                'false_accept': 0,
                'true_reject': 0,
                'unknown': 0
            }
        
        # Validate outcomes if not already done
        if 'outcome' not in df.columns:
            df = self.validate_outcomes(df)
        
        if 'outcome' not in df.columns:
            return {
                'true_accept': 0,
                'false_reject': 0,
                'false_accept': 0,
                'true_reject': 0,
                'unknown': 0
            }
        
        counts = df['outcome'].value_counts().to_dict()
        return {
            'true_accept': counts.get('true_accept', 0),
            'false_reject': counts.get('false_reject', 0),
            'false_accept': counts.get('false_accept', 0),
            'true_reject': counts.get('true_reject', 0),
            'unknown': counts.get('unknown', 0)
        }

