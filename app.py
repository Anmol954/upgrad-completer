import streamlit as st
import requests
import json

st.set_page_config(page_title="Chattees Biradri — upGrad Completer", page_icon="⚡", layout="wide")

HEADERS_BASE = {
    "Content-Type": "application/json;charset=UTF-8",
    "accept": "application/json, text/plain, */*",
    "origin": "https://learn.upgrad.com",
    "referer": "https://learn.upgrad.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.stApp { background: #0f172a; color: #e2e8f0; }
h1 { color: #e2e8f0 !important; }
.badge {
    background: #312e81; color: #a5b4fc;
    padding: 2px 12px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 700;
    display: inline-block; margin-left: 10px;
}
.stat-box {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 10px; padding: 16px; margin: 8px 0;
}
.success { color: #86efac; }
.error   { color: #fca5a5; }
.info    { color: #93c5fd; }
</style>
""", unsafe_allow_html=True)

st.markdown('# ⚡ Chattees Biradri <span class="badge">upGrad Auto-Completer</span>', unsafe_allow_html=True)
st.caption("Login once. Select modules. Mark complete — no video watching needed.")

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("auth_token", None), ("session_id", None), ("user_id", None),
              ("user_name", None), ("reg_id", None), ("step", 1),
              ("courses", []), ("selected_course", None), ("modules", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

def api_headers(extra={}):
    h = {**HEADERS_BASE, **extra}
    if st.session_state.auth_token:
        h["auth-token"] = st.session_state.auth_token
    if st.session_state.session_id:
        h["sessionid"] = st.session_state.session_id
    return h

def make_request(method, url, body=None, extra_headers={}):
    try:
        h = api_headers(extra_headers)
        r = requests.request(method, url, headers=h,
                             json=body, timeout=15)
        # Capture auth token from response headers
        tok = r.headers.get("auth-token") or r.headers.get("Auth-Token")
        if tok:
            st.session_state.auth_token = tok
        return r
    except Exception as e:
        return None

# ── LOGIN ─────────────────────────────────────────────────────────────────────
if not st.session_state.auth_token:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Step 1 — Phone Number")
        phone = st.text_input("Mobile Number", placeholder="+91 9876543210",
                              value="+91")
        if st.button("📱 Send OTP", use_container_width=True):
            if not phone or phone == "+91":
                st.error("Enter your phone number.")
            else:
                p = phone.strip()
                if not p.startswith("+"):
                    p = "+91" + p.replace(" ", "")[-10:]
                with st.spinner("Sending OTP..."):
                    r = make_request("POST",
                        "https://prod-auth-api.upgrad.com/apis/auth/v5/registration/phone",
                        {"phoneNumber": p})
                if r and r.status_code == 200:
                    data = r.json()
                    st.session_state.reg_id = data.get("registrationId")
                    st.session_state.step = 2
                    st.success(f"✅ OTP sent to {p}")
                else:
                    st.error(f"❌ Failed: {r.text if r else 'No response'}")

    with col2:
        st.markdown("#### Step 2 — Verify OTP")
        otp = st.text_input("Enter OTP", placeholder="Enter OTP",
                            disabled=(st.session_state.step < 2),
                            max_chars=6)
        if st.button("✅ Verify & Login", use_container_width=True,
                     disabled=(st.session_state.step < 2)):
            if not otp:
                st.error("Enter the OTP.")
            else:
                with st.spinner("Verifying..."):
                    r = make_request("POST",
                        "https://prod-auth-api.upgrad.com/apis/auth/v5/otp/validate",
                        {"otp": int(otp)})
                if r and r.status_code == 200:
                    # Get user info
                    r2 = make_request("GET",
                        "https://prod-learn-api.upgrad.com/apis/v3/lms-config/me")
                    if r2 and r2.status_code == 200:
                        me = r2.json()
                        user = me.get("user", me)
                        st.session_state.user_id = str(user.get("id", ""))
                        fname = user.get("firstname", "")
                        lname = user.get("lastname", "")
                        st.session_state.user_name = f"{fname} {lname}".strip() or user.get("name", "User")
                        st.success(f"✅ Welcome, {st.session_state.user_name}!")
                        st.rerun()
                    else:
                        st.error("Logged in but couldn't fetch user info.")
                else:
                    err = r.json().get("message", "Invalid OTP") if r else "No response"
                    st.error(f"❌ {err}")

# ── MAIN APP ──────────────────────────────────────────────────────────────────
else:
    # User bar
    ucol1, ucol2 = st.columns([6, 1])
    with ucol1:
        st.success(f"👤 Logged in as **{st.session_state.user_name}**")
    with ucol2:
        if st.button("Logout"):
            for k in ["auth_token","session_id","user_id","user_name",
                      "reg_id","step","courses","selected_course","modules"]:
                st.session_state[k] = None if k != "step" else 1
                if k in ["courses","modules"]: st.session_state[k] = []
            st.rerun()

    # Load courses
    if not st.session_state.courses:
        with st.spinner("Loading your courses..."):
            r = make_request("GET",
                "https://prod-learn-api.upgrad.com/apis/v3/enrollments"
                "?platform=web-learn-lite&pageNo=1&pageSize=20&enrolmentStatus=ALL")
            rp = make_request("GET",
                f"https://learnerprogress.upgrad.com/progress/courses"
                f"?userId={st.session_state.user_id}")
            if r and r.status_code == 200:
                enrolls = r.json()
                progs = rp.json() if rp and rp.status_code == 200 else {}
                st.session_state.courses = [
                    {
                        "id": (e.get("course") or e).get("id"),
                        "name": (e.get("course") or e).get("name", "Course"),
                        "progress": round(progs.get(
                            str((e.get("course") or e).get("id")), {}).get("userProgress", 0))
                    }
                    for e in (enrolls if isinstance(enrolls, list) else [])
                ]

    left, right = st.columns([1, 2])

    # ── Left: Course list ─────────────────────────────────────────────────────
    with left:
        st.markdown("#### 📚 Your Courses")
        for c in st.session_state.courses:
            label = f"{c['name']} ({c['progress']}%)"
            if st.button(label, key=f"course_{c['id']}", use_container_width=True):
                st.session_state.selected_course = c
                st.session_state.modules = []
                st.rerun()

    # ── Right: Modules ────────────────────────────────────────────────────────
    with right:
        if not st.session_state.selected_course:
            st.info("← Select a course to load its modules.")
        else:
            c = st.session_state.selected_course
            st.markdown(f"#### 📖 {c['name']}")

            # Load modules if not loaded
            if not st.session_state.modules:
                with st.spinner("Loading modules..."):
                    cid = c["id"]
                    uid = st.session_state.user_id

                    # Get module groups
                    mgr = make_request("GET",
                        f"https://prod-learn-api.upgrad.com/apis/v2/modulegroups"
                        f"?courseId={cid}&specialisationKey={cid}_default")

                    if mgr and mgr.status_code == 200:
                        mgs = mgr.json()
                        all_modules = []

                        for g in mgs:
                            for m in g.get("modules", []):
                                if not m.get("isPublished"):
                                    continue
                                mid = m["id"]
                                # Get segment progress
                                pr = make_request("GET",
                                    f"https://learnerprogress.upgrad.com/progress/module/{mid}"
                                    f"?courseId={cid}&level=segment&userId={uid}")

                                segs = []
                                pct = 0
                                if pr and pr.status_code == 200:
                                    pd = pr.json()
                                    pct = round(pd.get("userProgress", 0))
                                    for sess in pd.get("sessions", []):
                                        for seg in sess.get("segments", []):
                                            segs.append({
                                                "id": seg["id"],
                                                "done": seg.get("isSegmentComplete", False)
                                            })

                                all_modules.append({
                                    "id": mid,
                                    "name": m["name"],
                                    "group": g["name"],
                                    "pct": pct,
                                    "segs": segs,
                                    "included": m.get("isIncludedInProgress", True)
                                })

                        st.session_state.modules = all_modules

            if st.session_state.modules:
                modules = st.session_state.modules

                # Selection controls
                bcol1, bcol2, bcol3 = st.columns(3)
                with bcol1:
                    if st.button("☑ Select All"):
                        for m in modules: m["selected"] = True
                        st.rerun()
                with bcol2:
                    if st.button("☐ Select None"):
                        for m in modules: m["selected"] = False
                        st.rerun()
                with bcol3:
                    if st.button("⏳ Incomplete Only"):
                        for m in modules: m["selected"] = m["pct"] < 100
                        st.rerun()

                st.markdown("---")

                # Group modules
                groups = {}
                for m in modules:
                    groups.setdefault(m["group"], []).append(m)

                for gname, gmods in groups.items():
                    st.markdown(f"**{gname}**")
                    for m in gmods:
                        incomplete = len([s for s in m["segs"] if not s["done"]])
                        pct = m["pct"]
                        icon = "✅" if pct == 100 else "⏳" if pct > 0 else "🔴"
                        label = f"{icon} {m['name']} — {pct}% ({incomplete} remaining)"
                        m["selected"] = st.checkbox(label, value=m.get("selected", pct < 100),
                                                     key=f"mod_{m['id']}")

                st.markdown("---")

                selected = [m for m in modules if m.get("selected")]
                total_segs = sum(len([s for s in m["segs"] if not s["done"]]) for m in selected)
                st.info(f"**{len(selected)} modules selected** · {total_segs} segments to complete")

                if st.button("🚀 Mark Selected as Complete", type="primary",
                             use_container_width=True, disabled=len(selected) == 0):

                    cid = st.session_state.selected_course["id"]
                    uid = st.session_state.user_id
                    progress_bar = st.progress(0)
                    status_box = st.empty()
                    results = []
                    total_done = 0
                    total_total = total_segs or 1

                    for m in selected:
                        todo = [s for s in m["segs"] if not s["done"]]
                        if not todo:
                            results.append(f"✅ **{m['name']}** — already complete")
                            continue

                        ok = 0
                        fail = 0
                        for seg in todo:
                            r = make_request("PUT",
                                f"https://learnerprogress.upgrad.com/progress?userId={uid}",
                                {"completed": True, "componentId": seg["id"], "percentComplete": 100},
                                {"courseid": str(cid)})
                            if r and r.status_code == 200:
                                d = r.json()
                                if d.get("completed") or d.get("isSegmentComplete"):
                                    ok += 1
                                else:
                                    fail += 1
                            else:
                                fail += 1
                            total_done += 1
                            progress_bar.progress(total_done / total_total)
                            status_box.info(f"Processing **{m['name']}**... {ok}/{len(todo)} done")

                        if fail == 0:
                            results.append(f"✅ **{m['name']}** — all {ok} segments complete")
                        else:
                            results.append(f"⚠️ **{m['name']}** — {ok} ok, {fail} failed")

                    progress_bar.progress(1.0)
                    status_box.empty()

                    st.markdown("### Results")
                    for r in results:
                        st.markdown(r)

                    # Refresh modules
                    st.session_state.modules = []
                    st.success("Done! Click the course again to see updated progress.")
