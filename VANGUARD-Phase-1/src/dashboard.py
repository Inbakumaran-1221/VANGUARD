"""
Streamlit interactive dashboard for accessibility auditor.
Provides web UI for data upload, visualization, and report exploration.
"""

import io
import logging
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Fix Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go

from src.pipeline import run_audit_pipeline
from src.pdf_reporter import generate_pdf_report
from src.utils import setup_logging, get_logger

# Setup logging
setup_logging(logging.INFO)
logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="Accessibility Auditor",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .critical { color: #d32f2f; font-weight: bold; }
    .high { color: #f57c00; font-weight: bold; }
    .medium { color: #fbc02d; font-weight: bold; }
    .low { color: #388e3c; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_session():
    """Initialize session state."""
    if 'report' not in st.session_state:
        st.session_state.report = None
    if 'pipeline' not in st.session_state:
        st.session_state.pipeline = None
    if 'scores' not in st.session_state:
        st.session_state.scores = None


def render_header():
    """Render page header."""
    col1, col2 = st.columns([0.8, 0.2])
    
    with col1:
        st.title("♿ Accessibility Auditor")
        st.markdown("### AI-Powered Gap Detection for Urban Public Transport")
    
    with col2:
        st.write("")
        st.write("")
        if st.session_state.get("report") is not None:
            st.success("✓ Analysis Complete")


def render_data_upload_section():
    """Render data upload section."""
    st.header("📊 Data Upload & Analysis")
    
    with st.expander("Upload Data", expanded=st.session_state.get("report") is None):
        col1, col2 = st.columns(2)
        
        with col1:
            city_name = st.text_input("City Name", value="Sample City")
        
        with col2:
            data_source = st.radio(
                "Data Source",
                ["Demo/Synthetic Data", "Upload CSV Files"],
                key="data_source"
            )
        
        use_mock = data_source == "Demo/Synthetic Data"
        
        stops_file = None
        grievances_file = None
        
        if not use_mock:
            col1, col2 = st.columns(2)
            
            with col1:
                stops_file = st.file_uploader(
                    "Upload Stops CSV",
                    type="csv",
                    key="stops_upload",
                    help="CSV with columns: id, name, latitude, longitude, stop_type, has_ramp, has_audio_signals, etc."
                )
            
            with col2:
                grievances_file = st.file_uploader(
                    "Upload Grievances CSV",
                    type="csv",
                    key="grievances_upload",
                    help="CSV with columns: id, stop_id, text, severity, timestamp"
                )
        
        if st.button("▶ Run Audit Analysis", key="run_analysis"):
            with st.spinner("Running accessibility audit..."):
                try:
                    # Save uploaded files to temp directory
                    temp_dir = Path(tempfile.mkdtemp())
                    
                    stops_path = None
                    grievances_path = None
                    
                    if stops_file and not use_mock:
                        stops_path = temp_dir / "stops.csv"
                        with open(stops_path, "wb") as f:
                            f.write(stops_file.getbuffer())
                    
                    if grievances_file and not use_mock:
                        grievances_path = temp_dir / "grievances.csv"
                        with open(grievances_path, "wb") as f:
                            f.write(grievances_file.getbuffer())
                    
                    # Run pipeline
                    report, pipeline = run_audit_pipeline(
                        city_name=city_name,
                        stops_source=str(stops_path) if stops_path else None,
                        grievances_source=str(grievances_path) if grievances_path else None,
                        use_mock=use_mock,
                        clustering_method='tfidf'
                    )
                    
                    # Cache results
                    st.session_state.report = report
                    st.session_state.pipeline = pipeline
                    st.session_state.scores = pipeline.scores
                    
                    st.success(f"✓ Audit complete! Report ID: {report.report_id}")
                
                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")
                    logger.error(f"Pipeline error: {e}", exc_info=True)


def render_overview_tab():
    """Render overview tab."""
    report = st.session_state.get("report")
    if not report:
        st.info("Please upload data and run analysis first.")
        return
    
    st.subheader("📈 Audit Summary")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Stops Audited", report.total_stops_audited)
    
    with col2:
        st.metric("Grievances Analyzed", report.total_grievances_analyzed)
    
    with col3:
        st.metric("Coverage", f"{report.coverage_percent:.1f}%")
    
    with col4:
        st.metric("Avg Gap Score", f"{report.avg_gap_score:.1f}/100")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Data Source", report.data_source.upper())
    with col_b:
        st.metric("Image Mode", report.image_detector_mode or "N/A")
    with col_c:
        precision = report.evaluation_metrics.get("precision") if report.evaluation_metrics else None
        st.metric("Precision", f"{precision:.3f}" if precision is not None else "N/A")
    
    # Priority distribution
    st.subheader("🎯 Priority Distribution")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        priority_data = {
            'Priority': ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
            'Count': [
                report.stops_by_priority['CRITICAL'],
                report.stops_by_priority['HIGH'],
                report.stops_by_priority['MEDIUM'],
                report.stops_by_priority['LOW'],
            ]
        }
        df_priority = pd.DataFrame(priority_data)
        
        fig = px.bar(
            df_priority,
            x='Priority',
            y='Count',
            color='Priority',
            color_discrete_map={
                'CRITICAL': '#d32f2f',
                'HIGH': '#f57c00',
                'MEDIUM': '#fbc02d',
                'LOW': '#388e3c',
            },
            title="Stops by Priority Level"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Priority Breakdown")
        st.markdown(f"🔴 **CRITICAL:** {report.stops_by_priority['CRITICAL']}")
        st.markdown(f"🟠 **HIGH:** {report.stops_by_priority['HIGH']}")
        st.markdown(f"🟡 **MEDIUM:** {report.stops_by_priority['MEDIUM']}")
        st.markdown(f"🟢 **LOW:** {report.stops_by_priority['LOW']}")
    
    # Key findings
    st.subheader("🔍 Key Findings")
    for i, finding in enumerate(report.key_findings, 1):
        st.markdown(f"{i}. {finding}")
    
    # Gap score distribution
    st.subheader("📊 Gap Score Distribution")
    
    if st.session_state.scores:
        gap_scores = [s.gap_score for s in st.session_state.scores]
        
        fig = px.histogram(
            x=gap_scores,
            nbins=20,
            title="Distribution of Accessibility Gap Scores",
            labels={'x': 'Gap Score (0-100)', 'y': 'Number of Stops'},
        )
        st.plotly_chart(fig, use_container_width=True)


def render_map_tab():
    """Render interactive map tab."""
    if not st.session_state.scores:
        st.info("Please run analysis first.")
        return
    
    st.subheader("🗺️ Priority Map")
    
    # Create map
    scores = st.session_state.scores
    
    if scores:
        center_lat = sum(s.latitude for s in scores) / len(scores)
        center_lon = sum(s.longitude for s in scores) / len(scores)
    else:
        center_lat, center_lon = 40.7128, -74.0060
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="OpenStreetMap"
    )
    
    # Add markers for each stop
    for score in scores:
        # Determine color by priority
        color_map = {
            'CRITICAL': 'red',
            'HIGH': 'orange',
            'MEDIUM': 'yellow',
            'LOW': 'green',
        }
        color = color_map.get(score.priority_level.value, 'blue')
        
        popup_text = f"""
        <b>{score.stop_name}</b><br/>
        Gap Score: {score.gap_score}/100<br/>
        Priority: {score.priority_level.value}<br/>
        Grievances: {score.grievance_count}<br/>
        Top Issues: {', '.join(score.top_themes[:2]) if score.top_themes else 'N/A'}
        """
        
        folium.CircleMarker(
            location=[score.latitude, score.longitude],
            radius=8,
            popup=folium.Popup(popup_text, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2,
        ).add_to(m)
    
    st_folium(m, width=1400, height=600)
    
    # Legend
    st.markdown("""
    **Legend:**
    - 🔴 Red = CRITICAL (Gap Score ≥ 80)
    - 🟠 Orange = HIGH (Gap Score 60-79)
    - 🟡 Yellow = MEDIUM (Gap Score 40-59)
    - 🟢 Green = LOW (Gap Score < 40)
    """)


def render_stops_tab():
    """Render stops detail tab."""
    scores = st.session_state.get("scores")
    if not scores:
        st.info("Please run analysis first.")
        return
    
    st.subheader("📍 Transit Stops - Detailed Analysis")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        priority_filter = st.multiselect(
            "Filter by Priority",
            options=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
            default=['CRITICAL', 'HIGH'],
        )
    
    with col2:
        gap_score_min = st.slider("Min Gap Score", 0.0, 100.0, 0.0)
        gap_score_max = st.slider("Max Gap Score", 0.0, 100.0, 100.0)
    
    with col3:
        search_term = st.text_input("Search Stop Name")
    
    # Filter data
    filtered_scores = [
        s for s in scores
        if s.priority_level.value in priority_filter
        and gap_score_min <= s.gap_score <= gap_score_max
        and (not search_term or search_term.lower() in s.stop_name.lower())
    ]
    
    # Display table
    df_display = pd.DataFrame([
        {
            'Stop Name': s.stop_name,
            'Gap Score': f"{s.gap_score:.1f}",
            'Priority': s.priority_level.value,
            'Grievances': s.grievance_count,
            'Top Issues': ', '.join(s.top_themes[:2]) if s.top_themes else 'N/A',
            'Cost': s.remediation_cost_estimate,
        }
        for s in filtered_scores
    ])
    
    st.dataframe(df_display, use_container_width=True)
    
    # Detailed view for selected stop
    if filtered_scores:
        st.subheader("📌 Stop Details")
        
        selected_stop_name = st.selectbox(
            "Select a stop to view details",
            [s.stop_name for s in filtered_scores]
        )
        
        selected_stop = next(s for s in filtered_scores if s.stop_name == selected_stop_name)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Gap Score", f"{selected_stop.gap_score}/100")
            st.metric("Priority", selected_stop.priority_level.value)
        
        with col2:
            st.metric("Grievances", selected_stop.grievance_count)
            st.metric("Remediation Cost", selected_stop.remediation_cost_estimate)
        
        with col3:
            st.metric("Latitude", f"{selected_stop.latitude:.4f}")
            st.metric("Longitude", f"{selected_stop.longitude:.4f}")
        
        st.markdown("**Top Grievance Themes:**")
        for theme in selected_stop.top_themes:
            st.markdown(f"- {theme}")
        
        st.markdown("**Recommendations:**")
        for rec in selected_stop.recommendations:
            st.markdown(f"- {rec}")


def render_themes_tab():
    """Render grievance themes tab."""
    report = st.session_state.get("report")
    if not report:
        st.info("Please run analysis first.")
        return
    
    st.subheader("📋 Grievance Themes Analysis")
    
    clusters = sorted(report.grievance_themes, key=lambda c: c.count, reverse=True)
    
    if clusters:
        # Top themes chart
        theme_data = {
            'Theme': [c.theme for c in clusters[:10]],
            'Count': [c.count for c in clusters[:10]],
        }
        df_themes = pd.DataFrame(theme_data)
        
        fig = px.bar(
            df_themes,
            x='Theme',
            y='Count',
            title="Top 10 Grievance Themes",
            labels={'Count': 'Number of Complaints'},
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Theme details table
        st.subheader("Theme Details")
        
        df_theme_details = pd.DataFrame([
            {
                'Theme': c.theme,
                'Count': c.count,
                'Top Keywords': ', '.join(c.top_keywords[:5]) if c.top_keywords else 'N/A',
                'Coherence': f"{c.silhouette_score:.2f}" if c.silhouette_score else 'N/A',
            }
            for c in clusters
        ])
        
        st.dataframe(df_theme_details, use_container_width=True)


def render_report_tab():
    """Render report download tab."""
    report = st.session_state.get("report")
    if not report:
        st.info("Please run analysis first.")
        return
    
    st.subheader("📄 Report Export")
    
    st.markdown(f"**Report ID:** {report.report_id}")
    st.markdown(f"**Generated:** {report.generated_at}")
    st.markdown(f"**Generation Time:** {report.generation_time_seconds}s")
    st.markdown(f"**Data Source:** {report.data_source.upper()}")
    st.markdown(f"**Image Detector Mode:** {report.image_detector_mode or 'N/A'}")

    if report.evaluation_metrics:
        st.markdown("### Evaluation Metrics")
        st.markdown(f"- Precision: {report.evaluation_metrics.get('precision', 0):.4f}")
        st.markdown(f"- Recall: {report.evaluation_metrics.get('recall', 0):.4f}")
        st.markdown(f"- F1 Score: {report.evaluation_metrics.get('f1_score', 0):.4f}")
        st.markdown(f"- Evaluated Stops: {int(report.evaluation_metrics.get('evaluated_stops', 0))}")
    
    # PDF download button
    if st.button("📥 Download PDF Report", key="download_pdf"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_bytes = generate_pdf_report(report)
                st.download_button(
                    label="Click to Download PDF",
                    data=pdf_bytes,
                    file_name=f"{report.report_id}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Failed to generate PDF: {e}")


def main():
    """Main app logic."""
    init_session()
    render_header()
    
    st.divider()
    
    render_data_upload_section()
    
    if st.session_state.get("report") is not None:
        st.divider()
        
        # Tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Overview",
            "🗺️ Map",
            "📍 Stops",
            "📋 Themes",
            "📄 Report",
            "ℹ️ Info",
        ])
        
        with tab1:
            render_overview_tab()
        
        with tab2:
            render_map_tab()
        
        with tab3:
            render_stops_tab()
        
        with tab4:
            render_themes_tab()
        
        with tab5:
            render_report_tab()
        
        with tab6:
            st.markdown("""
            ## About This Tool
            
            The **Accessibility Auditor** is an AI-powered system that analyzes urban public transport
            infrastructure to identify accessibility gaps for persons with disabilities.
            
            ### Key Features
            - **Grievance Analysis:** Clusters citizen complaints using NLP
            - **Accessibility Scoring:** Calculates gap scores based on missing features
            - **Priority Mapping:** Identifies stops needing immediate intervention
            - **Report Generation:** Exports comprehensive audit reports in PDF
            
            ### Data Used
            - Transit stop locations and features (from GTFS or open data)
            - Citizen grievances (from complaint portals or uploaded)
            - Optional ground truth checklist for precision/recall/F1 evaluation
            - Accessibility standards (WCAG 2.1, ADA guidelines)
            
            ### Supported Stop Types
            - Bus stops
            - Metro stations
            - Tram stops
            - Train stations
            
            ### Contact & Support
            For more information, visit the project repository or contact the development team.
            """)


if __name__ == "__main__":
    main()
