import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class StudentCharts:
    """
    Handles chart generation for student profile views.
    Student-specific visualizations.
    """

    @staticmethod
    def personal_attendance_timeline(daily_df):
        """
        Create personal attendance timeline line chart.
        
        Args:
            daily_df: DataFrame with 'date' and 'count' columns
            
        Returns:
            Plotly figure
        """
        if daily_df.empty:
            return None
        
        fig = px.line(
            daily_df,
            x='date',
            y='count',
            title='My Attendance Timeline',
            labels={'date': 'Date', 'count': 'Attendance Count'},
            markers=True,
            line_shape='linear'
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Attendance Count",
            hovermode='x unified',
            showlegend=False
        )
        fig.update_traces(line_color='#1f77b4', line_width=2)
        return fig

    @staticmethod
    def attendance_rate_gauge(attendance_rate):
        """
        Create attendance rate gauge chart.
        
        Args:
            attendance_rate: Attendance rate percentage (0-100)
            
        Returns:
            Plotly figure
        """
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=attendance_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Attendance Rate (%)"},
            delta={'reference': 80},  # Reference for comparison
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "gray"},
                    {'range': [80, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig.update_layout(height=300)
        return fig

    @staticmethod
    def score_trend_chart(score_df):
        """
        Create recognition score trend chart over time.
        
        Args:
            score_df: DataFrame with 'date' and 'avg_score' columns
            
        Returns:
            Plotly figure
        """
        if score_df.empty:
            return None
        
        fig = px.line(
            score_df,
            x='date',
            y='avg_score',
            title='Recognition Score Trend',
            labels={'date': 'Date', 'avg_score': 'Average Recognition Score'},
            markers=True
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Recognition Score",
            hovermode='x unified',
            yaxis=dict(range=[0, 1])  # Score range 0-1
        )
        fig.update_traces(line_color='#2ca02c', line_width=2)
        return fig

    @staticmethod
    def verification_success_chart(stats):
        """
        Create verification success breakdown chart.
        
        Args:
            stats: Dictionary with verification statistics
            
        Returns:
            Plotly figure
        """
        labels = ['Face Verified', 'Liveness Verified', 'Multi-Factor Verified']
        values = [
            stats.get('face_verification_rate', 0),
            stats.get('liveness_verification_rate', 0),
            stats.get('multi_factor_rate', 0)
        ]
        
        # Filter out zero values
        filtered_data = [(label, val) for label, val in zip(labels, values) if val > 0]
        if not filtered_data:
            return None
        
        labels, values = zip(*filtered_data)
        
        fig = px.bar(
            x=labels,
            y=values,
            title='Verification Success Rates',
            labels={'x': 'Verification Type', 'y': 'Success Rate (%)'},
            color=values,
            color_continuous_scale='Greens'
        )
        fig.update_layout(
            xaxis_title="Verification Type",
            yaxis_title="Success Rate (%)",
            yaxis=dict(range=[0, 100]),
            showlegend=False
        )
        return fig

    @staticmethod
    def weekly_attendance_pattern(attendance_df):
        """
        Create weekly attendance pattern chart (day of week).
        
        Args:
            attendance_df: DataFrame with attendance records including 'timestamp'
            
        Returns:
            Plotly figure
        """
        if attendance_df.empty or 'timestamp' not in attendance_df.columns:
            return None
        
        df = attendance_df.copy()
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.day_name()
        df['day_num'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        
        # Order by day of week
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekly = df.groupby(['day_of_week', 'day_num']).size().reset_index(name='count')
        weekly = weekly.sort_values('day_num')
        
        fig = px.bar(
            weekly,
            x='day_of_week',
            y='count',
            title='Weekly Attendance Pattern',
            labels={'day_of_week': 'Day of Week', 'count': 'Attendance Count'},
            color='count',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            xaxis_title="Day of Week",
            yaxis_title="Attendance Count",
            showlegend=False
        )
        return fig

