import streamlit as st
import pandas as pd

# -------------------------------------------------------------------
# RESET LOGIC
# -------------------------------------------------------------------
def reset_app():
    st.session_state.clear()
    st.stop()  # Halts the script here; the user must interact again to re-run

# -------------------------------------------------------------------
# 1) Load your master catalog
# -------------------------------------------------------------------
df = pd.read_excel(
    "../Airspan_Catalog.xlsx",
    sheet_name="Catalog",
    engine="openpyxl"
)

# -------------------------------------------------------------------
# 2) Identify which columns are the 'product family' columns
# -------------------------------------------------------------------
product_family_cols = [
    "AS1032","AS1035","AS1050","AH4200","AH4400","A5G7200",
    "AS1900","AS2900","AV1901","AV6200","AH4000","AS1000",
    "AS1030","AV1500","AV1000","AV1200","-"
]

# -------------------------------------------------------------------
# 3) Melt/unpivot
# -------------------------------------------------------------------
id_cols = [
    "Product Marketing number",
    "Active",
    "Group",
    "Tag",
    "Spectrum",
    "CBRS Only?",
    "Description",
    "List Price",
    "US List Price",
    "Configuration",
    "Comment"
]
melted_df = df.melt(
    id_vars=id_cols,
    value_vars=product_family_cols,
    var_name="ProductFamily",
    value_name="CategoryIndicator"
)

# -------------------------------------------------------------------
# 4) Filter out rows not part of the product family
# -------------------------------------------------------------------
df_families = melted_df[melted_df["CategoryIndicator"] == 1].copy()

# ===================================================================
# Streamlit App
# ===================================================================
st.title("Airspan Catalog")

# -- Initialize session state for product family
if "selected_family" not in st.session_state:
    st.session_state["selected_family"] = "-"  # default to dash

# -- Build a list of families, plus dash at the front
families = sorted(df_families["ProductFamily"].unique().tolist())
if "-" not in families:
    families.insert(0, "-")

# -- Reset button: set selected_family to dash
if st.button("Reset"):
    st.session_state["selected_family"] = "-"

# -- Product family selectbox
selected_family = st.selectbox(
    "Choose a product family",
    families,
    key="selected_family"  # ties to session state
)

st.write(f"Currently selected family: **{selected_family}**")

# -- If dash is chosen, skip all logic
if selected_family == "-":
    st.write("_No family selected. Please pick a product family._")
    st.stop()

# -- Filter the DataFrame by the chosen family, default config, etc.
filtered_data = df_families[
    (df_families["ProductFamily"] == selected_family) &
    (df_families["Configuration"] == "Default")
]

# Define custom Tag order
tag_order = [
    "Base Station",
    "Software",
    "ACP",
    "Antenna",
    "Cable",
    "Connector/Splitter/Adapter",
    "Filter",
    "Mounting Kit",
    "Multi-Accessory",
    "Power Supply",
    "Timing",
    "Extended Warranty",
    "ASPlus"
]

# Keep only relevant tags
filtered_data = filtered_data[filtered_data["Tag"].isin(tag_order)]
filtered_data["Tag"] = pd.Categorical(filtered_data["Tag"], categories=tag_order, ordered=True)
filtered_data = filtered_data.sort_values(by="Tag")

st.subheader("Filtered Catalog Items (Default Configuration)")
st.dataframe(filtered_data)

# -------------------------------------------------------------------
# Helper function for "auto‐select if only one, else multiselect"
# -------------------------------------------------------------------
def auto_select_or_multiselect(df_subset: pd.DataFrame, single_label: str, multi_label: str):
    """
    If df_subset has exactly 1 unique Description, auto-select it.
    Otherwise, present a multiselect for all unique Descriptions.
    Returns the chosen rows.
    """
    if df_subset.empty:
        return df_subset

    unique_desc = df_subset["Description"].unique()
    if len(unique_desc) == 1:
        # Auto‐select
        st.write(f"*Only one option: **{unique_desc[0]}** (selected automatically)*")
        return df_subset.copy()
    else:
        # Multiple items: user picks
        chosen = st.multiselect(multi_label, unique_desc)
        return df_subset[df_subset["Description"].isin(chosen)].copy()

# Lists/flags to track selections
all_chosen_items = []
is_cbrs = False
system_qty = 1

# ===================================================================
# Step 1: Base Station
# ===================================================================
st.subheader("Base Station Selection")
base_stations = filtered_data[filtered_data["Tag"] == "Base Station"]

if not base_stations.empty:
    # 1a) If only one spectrum is available, auto‐select it
    unique_specs = base_stations["Spectrum"].unique()
    if len(unique_specs) == 1:
        auto_spec = unique_specs[0]
        st.write(f"*Only one spectrum: **{auto_spec}** (auto‐selected)*")
        filtered_bs_data = base_stations[base_stations["Spectrum"] == auto_spec]
    else:
        selected_spec = st.selectbox("Which Spectrum Band do you want?", unique_specs)
        filtered_bs_data = base_stations[base_stations["Spectrum"] == selected_spec]

    st.write("Matching Base Stations:")
    st.dataframe(filtered_bs_data)

    if not filtered_bs_data.empty:
        chosen_bs_data = auto_select_or_multiselect(
            filtered_bs_data,
            single_label="Only one base station available",
            multi_label="Select the Base Station(s) you actually want:"
        )
        st.write("You selected:")
        st.dataframe(chosen_bs_data)

        if not chosen_bs_data.empty:
            system_qty = st.number_input(
                "How many total base station nodes do you need?",
                min_value=1,
                value=1
            )
            chosen_bs_data["Quantity"] = system_qty
            all_chosen_items.append(chosen_bs_data)

            # If any chosen base station is b48/n48 => is_cbrs = True
            specs_chosen = chosen_bs_data["Spectrum"].str.lower().unique()
            if any(s in ["b48", "n48"] for s in specs_chosen):
                is_cbrs = True

# ===================================================================
# Step 2: Software (CBRS = extras)
# ===================================================================
st.subheader("Software Selection")
software_items = filtered_data[filtered_data["Tag"] == "Software"]

if not software_items.empty:
    # Normal software
    normal_sw = software_items[software_items["CBRS Only?"] != 1]
    # CBRS-only software
    cbrs_sw = software_items[software_items["CBRS Only?"] == 1]

    # Let user pick from normal software (always available)
    chosen_sw_normal = pd.DataFrame()
    if not normal_sw.empty:
        st.write("Available NORMAL Software Items:")
        st.dataframe(normal_sw)
        chosen_sw_normal = auto_select_or_multiselect(
            normal_sw,
            single_label="Only one normal software item available.",
            multi_label="Pick your normal software items"
        )

    # If CBRS => automatically add cbrs_sw
    chosen_sw_cbrs = pd.DataFrame()
    if is_cbrs and not cbrs_sw.empty:
        st.write("**Because you selected b48/n48, the following CBRS-only Software items are auto‐included:**")
        st.dataframe(cbrs_sw)
        chosen_sw_cbrs = cbrs_sw.copy()

    # Combine them
    chosen_sw_data = pd.concat([chosen_sw_normal, chosen_sw_cbrs]).drop_duplicates()
    if not chosen_sw_data.empty:
        chosen_sw_data["Quantity"] = system_qty
        st.write("Software items selected:")
        st.dataframe(chosen_sw_data)
        all_chosen_items.append(chosen_sw_data)

# ===================================================================
# Step 3: ACP (CBRS = extras)
# ===================================================================
st.subheader("ACP Selection")
acp_items = filtered_data[filtered_data["Tag"] == "ACP"]

if not acp_items.empty:
    normal_acp = acp_items[acp_items["CBRS Only?"] != 1]
    cbrs_acp = acp_items[acp_items["CBRS Only?"] == 1]

    chosen_acp_normal = pd.DataFrame()
    if not normal_acp.empty:
        st.write("Available NORMAL ACP Items:")
        st.dataframe(normal_acp)
        chosen_acp_normal = auto_select_or_multiselect(
            normal_acp,
            single_label="Only one normal ACP item available.",
            multi_label="Pick your ACP items"
        )

    chosen_acp_cbrs = pd.DataFrame()
    if is_cbrs and not cbrs_acp.empty:
        st.write("**Because you selected b48/n48, the following CBRS-only ACP items are auto‐included:**")
        st.dataframe(cbrs_acp)
        chosen_acp_cbrs = cbrs_acp.copy()

    chosen_acp_data = pd.concat([chosen_acp_normal, chosen_acp_cbrs]).drop_duplicates()
    if not chosen_acp_data.empty:
        chosen_acp_data["Quantity"] = system_qty
        st.write("ACP items selected:")
        st.dataframe(chosen_acp_data)
        all_chosen_items.append(chosen_acp_data)

# ===================================================================
# Step 4: Antenna
# ===================================================================
st.subheader("Antenna Selection")
antenna_items = filtered_data[filtered_data["Tag"] == "Antenna"]

if not antenna_items.empty:
    st.write("Available Antennas:")
    st.dataframe(antenna_items)
    chosen_antenna = auto_select_or_multiselect(
        antenna_items,
        single_label="Only one antenna available.",
        multi_label="Pick your antenna(s)"
    )
    if not chosen_antenna.empty:
        chosen_antenna["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_antenna)
        all_chosen_items.append(chosen_antenna)

# ===================================================================
# Step 5: Cable
# ===================================================================
st.subheader("Cable Selection")
cable_items = filtered_data[filtered_data["Tag"] == "Cable"]

if not cable_items.empty:
    st.write("Available Cable Items:")
    st.dataframe(cable_items)
    chosen_cable = auto_select_or_multiselect(
        cable_items,
        single_label="Only one cable available.",
        multi_label="Pick your cable(s)"
    )
    if not chosen_cable.empty:
        chosen_cable["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_cable)
        all_chosen_items.append(chosen_cable)

# ===================================================================
# Step 6: Connector/Splitter/Adapter
# ===================================================================
st.subheader("Connector / Splitter / Adapter")
conn_items = filtered_data[filtered_data["Tag"] == "Connector/Splitter/Adapter"]

if not conn_items.empty:
    st.write("Available Connectors/Splitters/Adapters:")
    st.dataframe(conn_items)
    chosen_conn = auto_select_or_multiselect(
        conn_items,
        single_label="Only one connector/adapter available.",
        multi_label="Pick your connector/splitter/adapter(s)"
    )
    if not chosen_conn.empty:
        chosen_conn["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_conn)
        all_chosen_items.append(chosen_conn)

# ===================================================================
# Step 7: Filter
# ===================================================================
st.subheader("Filter Selection")
filter_items = filtered_data[filtered_data["Tag"] == "Filter"]

if not filter_items.empty:
    st.write("Available Filters:")
    st.dataframe(filter_items)
    chosen_filter = auto_select_or_multiselect(
        filter_items,
        single_label="Only one filter available.",
        multi_label="Pick your filter(s)"
    )
    if not chosen_filter.empty:
        chosen_filter["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_filter)
        all_chosen_items.append(chosen_filter)

# ===================================================================
# Step 8: Mounting Kit
# ===================================================================
st.subheader("Mounting Kit Selection")
mk_items = filtered_data[filtered_data["Tag"] == "Mounting Kit"]

if not mk_items.empty:
    st.write("Available Mounting Kits:")
    st.dataframe(mk_items)
    chosen_mk = auto_select_or_multiselect(
        mk_items,
        single_label="Only one mounting kit available.",
        multi_label="Pick your mounting kit(s)"
    )
    if not chosen_mk.empty:
        chosen_mk["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_mk)
        all_chosen_items.append(chosen_mk)

# ===================================================================
# Step 9: Multi-Accessory
# ===================================================================
st.subheader("Multi-Accessory Selection")
ma_items = filtered_data[filtered_data["Tag"] == "Multi-Accessory"]

if not ma_items.empty:
    st.write("Available Multi-Accessory Items:")
    st.dataframe(ma_items)
    chosen_ma = auto_select_or_multiselect(
        ma_items,
        single_label="Only one multi-accessory item available.",
        multi_label="Pick your multi-accessories"
    )
    if not chosen_ma.empty:
        chosen_ma["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_ma)
        all_chosen_items.append(chosen_ma)

# ===================================================================
# Step 10: Power Supply
# ===================================================================
st.subheader("Power Supply Selection")
ps_items = filtered_data[filtered_data["Tag"] == "Power Supply"]

if not ps_items.empty:
    st.write("Available Power Supplies:")
    st.dataframe(ps_items)
    chosen_ps = auto_select_or_multiselect(
        ps_items,
        single_label="Only one power supply available.",
        multi_label="Pick your power supply(s)"
    )
    if not chosen_ps.empty:
        chosen_ps["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_ps)
        all_chosen_items.append(chosen_ps)

# ===================================================================
# Step 11: Timing
# ===================================================================
st.subheader("Timing Selection")
timing_items = filtered_data[filtered_data["Tag"] == "Timing"]

if not timing_items.empty:
    st.write("Available Timing Items:")
    st.dataframe(timing_items)
    chosen_timing = auto_select_or_multiselect(
        timing_items,
        single_label="Only one timing item available.",
        multi_label="Pick your timing item(s)"
    )
    if not chosen_timing.empty:
        chosen_timing["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_timing)
        all_chosen_items.append(chosen_timing)

# ===================================================================
# Step 12: Extended Warranty
# ===================================================================
st.subheader("Extended Warranty Selection")
ew_items = filtered_data[filtered_data["Tag"] == "Extended Warranty"]

if not ew_items.empty:
    st.write("Available Extended Warranties:")
    st.dataframe(ew_items)
    chosen_ew = auto_select_or_multiselect(
        ew_items,
        single_label="Only one extended warranty available.",
        multi_label="Pick your extended warranty item(s)"
    )
    if not chosen_ew.empty:
        chosen_ew["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_ew)
        all_chosen_items.append(chosen_ew)

# ===================================================================
# Step 13: ASPlus (CBRS is ALTERNATIVE, not additional)
# ===================================================================
st.subheader("ASPlus Selection")
asplus_items = filtered_data[filtered_data["Tag"] == "ASPlus"]

if not asplus_items.empty:
    # normal vs cbrs
    normal_asplus = asplus_items[asplus_items["CBRS Only?"] != 1]
    cbrs_asplus   = asplus_items[asplus_items["CBRS Only?"] == 1]

    if is_cbrs:
        st.write("**Because you selected b48/n48, only CBRS variant of ASPlus is available**")
        if not cbrs_asplus.empty:
            st.dataframe(cbrs_asplus)
            chosen_asplus = auto_select_or_multiselect(
                cbrs_asplus,
                single_label="Only one CBRS ASPlus item available.",
                multi_label="Pick your CBRS ASPlus item(s)"
            )
        else:
            chosen_asplus = pd.DataFrame()
    else:
        st.write("**Non‐CBRS**: choose from the normal ASPlus items.")
        if not normal_asplus.empty:
            st.dataframe(normal_asplus)
            chosen_asplus = auto_select_or_multiselect(
                normal_asplus,
                single_label="Only one normal ASPlus item available.",
                multi_label="Pick your normal ASPlus item(s)"
            )
        else:
            chosen_asplus = pd.DataFrame()

    if not chosen_asplus.empty:
        chosen_asplus["Quantity"] = system_qty
        st.write("You selected:")
        st.dataframe(chosen_asplus)
        all_chosen_items.append(chosen_asplus)

# -------------------------------------------------------------------
# FINAL STEP: Optional/Spare Items
# -------------------------------------------------------------------
st.write("---")
st.subheader("Additional Optional/Spare Items")

spare_df = df_families[
    (df_families["ProductFamily"] == selected_family) &
    (df_families["Active"] == 1) &
    (df_families["Configuration"] == "Optional/Spare")
]

spare_df["Tag"] = pd.Categorical(spare_df["Tag"], categories=tag_order, ordered=True)
spare_df = spare_df.sort_values(by="Tag")

st.write("Below are optional/spare items you may add to your order:")
st.dataframe(spare_df)

if not spare_df.empty:
    row_ids_spare = spare_df.index.tolist()
    chosen_spare_rows = st.multiselect(
        "Select any optional/spare items you’d like:",
        row_ids_spare,
        format_func=lambda x: spare_df.loc[x, "Description"]
    )
    chosen_spare_data = spare_df.loc[chosen_spare_rows].copy()
    chosen_spare_data["Quantity"] = system_qty

    st.write("You selected the following optional/spare items:")
    st.dataframe(chosen_spare_data)

    if not chosen_spare_data.empty:
        all_chosen_items.append(chosen_spare_data)

# -------------------------------------------------------------------
# Summarize Final Selections
# -------------------------------------------------------------------
st.write("---")
st.subheader("Final Chosen Items (All Steps)")

if all_chosen_items:
    final_selection = pd.concat(all_chosen_items, ignore_index=True).drop_duplicates()

    # Convert US List Price to numeric
    final_selection["US List Price"] = pd.to_numeric(final_selection["US List Price"], errors="coerce")

    # We'll hide certain columns and then display an editable table for the user to adjust Quantity
    cols_to_hide = [
        "Active", "CBRS Only?", "Spectrum",
        "List Price", "ProductFamily", "CategoryIndicator"
    ]
    final_display = final_selection.drop(columns=cols_to_hide, errors="ignore").copy()

    if "Extended Price" in final_display.columns:
        final_display.drop(columns=["Extended Price"], inplace=True)

    # Use st.data_editor to let user tweak "Quantity"
    edited_df = st.data_editor(
        final_display,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Quantity": st.column_config.NumberColumn(min_value=0, step=1),
            "US List Price": st.column_config.NumberColumn(min_value=0.0, format="%.2f")
        },
        key="final_edit"
    )

    # Re-inject Extended Price
    edited_df["Extended Price"] = edited_df["US List Price"] * edited_df["Quantity"]

    st.write("**Final Selection (Quantities Editable)**")
    st.dataframe(edited_df, use_container_width=True)

    total_price = edited_df["Extended Price"].sum()
    st.write(f"**Total Extended Price**: {total_price:,.2f}")

else:
    st.write("No items selected yet.")

# -- RESET BUTTON (BOTTOM) --
if st.button("Reset", key="reset_bottom"):
    reset_app()
