import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server environments
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from app.utils.logging import setup_logger


class EvaluationPlots:
    """
    Generates evaluation visualizations for biometric performance analysis.
    Supports both matplotlib (for exports) and plotly (for interactive dashboards).
    """

    def __init__(self):
        self.logger = setup_logger()

    def score_distribution_histogram(self, df: pd.DataFrame, bins: int = 30, backend: str = 'plotly'):
        """
        Create histogram of recognition score distribution.
        
        Args:
            df: DataFrame with attendance records
            bins: Number of histogram bins
            backend: 'plotly' or 'matplotlib'
            
        Returns:
            Plotly figure or matplotlib figure
        """
        if df.empty or 'recognition_score' not in df.columns:
            self.logger.warning("Cannot create score distribution: missing data or recognition_score column")
            return None
        
        scores = df['recognition_score'].dropna()
        if len(scores) == 0:
            return None
        
        if backend == 'plotly':
            fig = px.histogram(
                df,
                x='recognition_score',
                nbins=bins,
                title='Recognition Score Distribution',
                labels={'recognition_score': 'Similarity Score', 'count': 'Frequency'},
                marginal="box"
            )
            fig.update_layout(
                xaxis_title="Similarity Score",
                yaxis_title="Frequency",
                hovermode='x unified'
            )
            return fig
        else:  # matplotlib
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(scores, bins=bins, edgecolor='black', alpha=0.7)
            ax.set_xlabel('Similarity Score')
            ax.set_ylabel('Frequency')
            ax.set_title('Recognition Score Distribution')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            return fig

    def genuine_vs_impostor_distribution(self, df: pd.DataFrame, bins: int = 30, backend: str = 'plotly'):
        """
        Create separate histograms for genuine and impostor score distributions.
        
        Args:
            df: DataFrame with attendance records
            bins: Number of histogram bins
            backend: 'plotly' or 'matplotlib'
            
        Returns:
            Plotly figure or matplotlib figure
        """
        if df.empty or 'face_verified' not in df.columns or 'recognition_score' not in df.columns:
            return None
        
        genuine = df[df['face_verified'] == 1]['recognition_score'].dropna()
        impostor = df[df['face_verified'] == 0]['recognition_score'].dropna()
        
        if len(genuine) == 0 and len(impostor) == 0:
            return None
        
        if backend == 'plotly':
            fig = go.Figure()
            
            if len(genuine) > 0:
                fig.add_trace(go.Histogram(
                    x=genuine,
                    name='Genuine',
                    opacity=0.7,
                    nbinsx=bins,
                    marker_color='green'
                ))
            
            if len(impostor) > 0:
                fig.add_trace(go.Histogram(
                    x=impostor,
                    name='Impostor',
                    opacity=0.7,
                    nbinsx=bins,
                    marker_color='red'
                ))
            
            fig.update_layout(
                title='Genuine vs Impostor Score Distribution',
                xaxis_title='Similarity Score',
                yaxis_title='Frequency',
                barmode='overlay',
                hovermode='x unified'
            )
            return fig
        else:  # matplotlib
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if len(genuine) > 0:
                ax.hist(genuine, bins=bins, alpha=0.7, label='Genuine', color='green', edgecolor='black')
            
            if len(impostor) > 0:
                ax.hist(impostor, bins=bins, alpha=0.7, label='Impostor', color='red', edgecolor='black')
            
            ax.set_xlabel('Similarity Score')
            ax.set_ylabel('Frequency')
            ax.set_title('Genuine vs Impostor Score Distribution')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            return fig

    def far_frr_curve(self, df: pd.DataFrame, num_thresholds: int = 50, backend: str = 'plotly'):
        """
        Create FAR/FRR curve across threshold range.
        
        Args:
            df: DataFrame with attendance records
            num_thresholds: Number of threshold points
            backend: 'plotly' or 'matplotlib'
            
        Returns:
            Plotly figure or matplotlib figure
        """
        from app.analytics.evaluation import AttendanceEvaluation
        
        evaluator = AttendanceEvaluation()
        sweep_df = evaluator.compute_metrics_sweep(df, num_thresholds)
        
        if sweep_df.empty:
            return None
        
        if backend == 'plotly':
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=sweep_df['threshold'],
                y=sweep_df['FAR'],
                mode='lines',
                name='FAR (False Acceptance Rate)',
                line=dict(color='red', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=sweep_df['threshold'],
                y=sweep_df['FRR'],
                mode='lines',
                name='FRR (False Rejection Rate)',
                line=dict(color='blue', width=2)
            ))
            
            # Add EER point
            eer_result = evaluator.find_eer_threshold(df)
            if eer_result['eer_value'] > 0:
                fig.add_trace(go.Scatter(
                    x=[eer_result['eer_threshold']],
                    y=[eer_result['eer_value']],
                    mode='markers',
                    name=f"EER (Threshold: {eer_result['eer_threshold']:.3f})",
                    marker=dict(size=12, color='black', symbol='star')
                ))
            
            fig.update_layout(
                title='FAR / FRR vs Threshold',
                xaxis_title='Threshold',
                yaxis_title='Rate',
                hovermode='x unified',
                yaxis=dict(range=[0, 1])
            )
            return fig
        else:  # matplotlib
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ax.plot(sweep_df['threshold'], sweep_df['FAR'], label='FAR (False Acceptance Rate)', 
                   color='red', linewidth=2)
            ax.plot(sweep_df['threshold'], sweep_df['FRR'], label='FRR (False Rejection Rate)', 
                   color='blue', linewidth=2)
            
            # Add EER point
            eer_result = evaluator.find_eer_threshold(df)
            if eer_result['eer_value'] > 0:
                ax.plot(eer_result['eer_threshold'], eer_result['eer_value'], 
                       'k*', markersize=15, label=f"EER (Threshold: {eer_result['eer_threshold']:.3f})")
            
            ax.set_xlabel('Threshold')
            ax.set_ylabel('Rate')
            ax.set_title('FAR / FRR vs Threshold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.set_ylim([0, 1])
            plt.tight_layout()
            return fig

    def accuracy_curve(self, df: pd.DataFrame, num_thresholds: int = 50, backend: str = 'plotly'):
        """
        Create accuracy curve across threshold range.
        
        Args:
            df: DataFrame with attendance records
            num_thresholds: Number of threshold points
            backend: 'plotly' or 'matplotlib'
            
        Returns:
            Plotly figure or matplotlib figure
        """
        from app.analytics.evaluation import AttendanceEvaluation
        
        evaluator = AttendanceEvaluation()
        sweep_df = evaluator.compute_metrics_sweep(df, num_thresholds)
        
        if sweep_df.empty:
            return None
        
        if backend == 'plotly':
            fig = px.line(
                sweep_df,
                x='threshold',
                y='accuracy',
                title='Accuracy vs Threshold',
                labels={'threshold': 'Threshold', 'accuracy': 'Accuracy'},
                markers=True
            )
            fig.update_layout(
                xaxis_title='Threshold',
                yaxis_title='Accuracy',
                hovermode='x unified',
                yaxis=dict(range=[0, 1])
            )
            return fig
        else:  # matplotlib
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(sweep_df['threshold'], sweep_df['accuracy'], linewidth=2, color='green')
            ax.set_xlabel('Threshold')
            ax.set_ylabel('Accuracy')
            ax.set_title('Accuracy vs Threshold')
            ax.grid(True, alpha=0.3)
            ax.set_ylim([0, 1])
            plt.tight_layout()
            return fig

    def save_matplotlib_figure(self, fig, filepath: Path, dpi: int = 300):
        """
        Save matplotlib figure to file.
        
        Args:
            fig: Matplotlib figure
            filepath: Path to save file
            dpi: Resolution (default: 300)
        """
        if fig is None:
            self.logger.warning(f"Cannot save figure: figure is None")
            return
        
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(filepath, dpi=dpi, bbox_inches='tight')
            self.logger.info(f"Saved figure to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save figure to {filepath}: {e}")

