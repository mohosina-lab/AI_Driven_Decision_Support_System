import streamlit as st

knowledge_model = {

    "Production Stage": {
        "Design": "Low",
        "Assembly": "Medium",
        "Testing": "High"
    },

    "Component Availability": {
        "Available": "Low",
        "Limited": "Medium",
        "Unavailable": "High"
    },

    "Production Workload": {
        "Low": "Low",
        "Medium": "Medium",
        "High": "High"
    },

    "Delivery Deadline": {
        "Flexible": "Low",
        "Fixed": "High"
    }
}

st.title("Customer Change Request Simulator")

st.info(
    """
    The simulator allows users to model a customer change request scenario.

    Based on project assumptions and dependency relationships across organisational functions, the simulator evaluates the expected operational impact and highlights the factors contributing most to the result.
    """
)

st.subheader("Scenario Inputs")

production_stage = st.selectbox(
    "Production Stage",
    ["Design", "Assembly", "Testing"]
)

component_availability = st.selectbox(
    "Component Availability",
    ["Available", "Limited", "Unavailable"]
)

production_workload = st.selectbox(
    "Production Workload",
    ["Low", "Medium", "High"]
)

delivery_deadline = st.selectbox(
    "Delivery Deadline",
    ["Flexible", "Fixed"]
)

simulate = st.button("Run Simulation")


if simulate:

    st.subheader("Scenario Summary")

    st.write("**Production Stage:**", production_stage)

    st.write("**Component Availability:**", component_availability)

    st.write("**Production Workload:**", production_workload)

    st.write("**Delivery Deadline:**", delivery_deadline)

    scenario_impacts = [

        knowledge_model["Production Stage"][production_stage],

        knowledge_model["Component Availability"][component_availability],

        knowledge_model["Production Workload"][production_workload],

        knowledge_model["Delivery Deadline"][delivery_deadline]
    ]

    st.subheader("Impact Analysis")

    impact_score = {
    "Low": 1,
    "Medium": 2,
    "High": 3
    }

    scores = [impact_score[i] for i in scenario_impacts]

    average_score = sum(scores) / len(scores)

    if average_score <= 1.5:
        overall_impact = "LOW"

    elif average_score <= 2.5:
        overall_impact = "MEDIUM"

    else:
        overall_impact = "HIGH"

    st.success(f"Overall Impact Level: {overall_impact}")

    st.subheader("Impact Contributors")

    import pandas as pd

    contributors = pd.DataFrame({

        "Factor": [
        "Production Stage",
        "Component Availability",
        "Production Workload",
        "Delivery Deadline"
        ],

        "Impact": [
        knowledge_model["Production Stage"][production_stage],
        knowledge_model["Component Availability"][component_availability],
        knowledge_model["Production Workload"][production_workload],
        knowledge_model["Delivery Deadline"][delivery_deadline]
        ]
    }      )

    st.table(contributors)

st.warning(
    """
    This is a prototype. The current impact model is based on documented assumptions
    and dependency mapping. The next phase is decision archaeology and expert interviews
    to validate and refine the relationships and impact levels.
    """
)