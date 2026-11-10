# Customer Change Request Simulator

## Windows setup

Stop the old app with Ctrl+C. Extract this ZIP into a new folder. Open the folder containing app.py, model.py and requirements.txt in VS Code. Open a PowerShell terminal there and run each line separately:

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501. Keep the terminal open; stop with Ctrl+C.
If already using a working active environment (venv), skip recreating and activating it and run the last two commands. Both app.py and model.py must remain in the same folder. Use `dir` to check you are in that folder; your original download had two nested folders with the same name.

## Demo

Default: replace a component in 50 cabinets, 30 already wired, at an assumed 1 hour of rewiring per cabinet. Result: 30 additional rewiring person-hours. Explore the five tabs and download the text summary.

For the original LOW scenario: set wired to 0, stage to Design, components to Available, workload to Low and deadline to Flexible. Try Unavailable components for a HIGH scenario. Invalid quantities show an error until corrected.

## Changes

- Request, quantities and editable rewiring assumption.
- Quantity validation and a Design-stage consistency check.
- Rewiring effort, impact reasons and leading factors.
- Department actions and dependencies, plus suggested checks for Sales.
- Comparison of the current scenario with the same request before wiring.
- Assumptions and source labels, explicit rules and summary download.
- Overall impact now uses the highest factor instead of averaging factors. A high factor cannot be averaged away. This rule is an unvalidated modelling assumption.

## Limits

Component replacement only. User-entered description is recorded, not interpreted by AI. This is a rule-based prototype, not a trained AI model. Inputs are synthetic; time assumptions, category rules and department dependencies are unvalidated. Use team consistency checks and follow the facilitator's no-interview instruction.

Rewiring hours exclude engineering, procurement, other production work and testing. Effort is not elapsed time or delivery delay. Costs and delivery dates are not calculated. Department actions are suggestions, not completed approvals. Inputs are not saved between sessions; download the summary to retain them.

## Dependencies and original files

app.py is the interface and model.py contains the rules. requirements.txt installs the dashboard dependency, Streamlit. requirements-original.txt preserves the original notebook dependency list and is not needed for this dashboard. Original notebooks and data are retained unchanged; notebooks have not been updated for the new model. Python 3.11 or newer is recommended, subject to dependency support for the installed Python version.

## Tests

From this folder: `python -m unittest discover -s tests -v`.
Tests cover the 30-hour example, before-wiring comparison, low/high conditions, invalid quantities, fractional hours and Streamlit input changes. They require Streamlit.

## Version 2: connected synthetic schedule

Open **Connected schedule**, now the first results tab. The synthetic default is:
Engineering 1 day + parts 2 days after approval + rewiring 3 days + Testing 1 day = 7 working days.
The reserved change window is 8 days, leaving 1 day spare. Changing parts lead time to 5 days produces 10 days, exceeding the window by 2 days.

This is NOT a full-order delivery forecast. Normal first-time assembly and other order activities, transport, holidays and financial costs are excluded. “Day 0” is the assessment moment, not a calendar date. Activities are sequential; no overlap is modelled. Rework capacity is constant and exclusively available for this change. Production duration is rewiring person-hours divided by capacity, rounded UP to whole working-day slots. Engineering and testing may use fractional days. Testing input includes the assumed testing queue. If there is no rewiring, production rework duration is zero; other activities still take time.

The qualitative Low/Medium/High factors remain independent of the numeric schedule. They do not automatically set parts days or capacity. Numeric assumptions, not qualitative categories, drive schedule calculations. Parts unavailable now can still have a known future lead time. Deadline flexibility does not change the available window automatically.

Uncheck a “known” checkbox to explore missing information: schedule outputs become Undetermined. Zero rework capacity blocks a schedule when rework is needed. Before-wiring and parts-delay comparisons keep all other inputs fixed. The stress test adds an editable number of days to BOTH Engineering and Testing; it is not a statistical confidence interval.

All figures belong to a fictional company and are synthetic. No interviews are required. Review the assumptions and edge cases within the team; these checks do not establish real-world validity. Discuss the acceptable validation method with the facilitator. No AI has been integrated; text entry is descriptive only.

## Updating your existing Windows app

1. In the VS Code terminal running the old app, press Ctrl+C.
2. Extract the updated ZIP to a different temporary folder.
3. Copy **app.py** and **model.py** from the new extracted folder into your existing project folder (the folder that already contains your working venv). Choose Replace for both files. Keep both files together.
4. In your existing terminal, run:

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

No extra package installation is required if the previous version ran. Refresh the browser. You should see “VERSION 2” and a “Connected schedule” tab. Use the original Windows setup steps above only for a completely new installation.

Automated checks: 10 tests covering calculation, chain propagation, boundaries, unknown inputs, zero capacity and Streamlit interactions.

## Easy Windows launcher

After extracting the complete project, double-click **Run_Simulator.bat** in the folder containing app.py. It uses the existing local venv or creates one with the Windows `py` launcher, installs Streamlit if missing, and starts the app. Keep its terminal open. Python must already be installed. The earlier PowerShell command remains an alternative.
