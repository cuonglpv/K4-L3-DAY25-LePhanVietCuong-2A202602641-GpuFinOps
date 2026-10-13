"""Reproducible analysis and short Vietnamese write-up for the submission."""
import json
from pathlib import Path
import pandas as pd
from missions._common import ROOT, catalog_by_type, num
from missions import carbon_scheduling, m4_allocation
from finops import pricing, sustainability as s


def build_analysis(r1, r2, r3, baseline, optimized):
    out = Path(ROOT) / "outputs"
    stages = r2["stages_daily"]
    budget = r2["reasoning_budget"]
    carbon = carbon_scheduling.run()
    r4 = m4_allocation.run(False)
    cat = catalog_by_type()
    lines = ["## Phạm vi và phương pháp", "",
        "Dữ liệu tổng hợp seed=25; giá là snapshot minh họa tháng 6/2026 của lab, không phải giá thị trường hiện tại. "
        "M2 so cùng input + output token; cache không giảm giá output, batch giảm 50% cả hóa đơn. "
        "Thứ tự phân rã là cascade → cache → batch; đóng góp phụ thuộc thứ tự, không cộng các tỷ lệ tiết kiệm độc lập.", "",
        "M3 và M5 quy đổi theo tháng 30 ngày. Tổng M5 là kịch bản của lab: dữ liệu chưa liên kết trực tiếp telemetry, "
        "workload và request nên cần kiểm tra lại trước khi dùng làm dự báo hóa đơn. Hai extension bên dưới được báo cáo riêng, "
        "không cộng vào tổng savings.", "",
        "## Unit economics và breakdown inference (M2)", "",
        f"Cùng **{r2['total_tokens']:,} token/ngày**, 2.400 request; lặp 30 ngày cho bảng tháng.", "",
        "| Bước | USD/ngày | USD/30 ngày | $/1M-token | Tiết kiệm tăng thêm USD/ngày |",
        "|---|---:|---:|---:|---:|"]
    previous = stages["baseline"]
    for label, cost in stages.items():
        lines.append(f"| {label} | {cost:.6f} | {cost*30:.4f} | {pricing.dollars_per_million(cost,r2['total_tokens']):.6f} | {previous-cost:.6f} |")
        previous = cost
    lines += ["", f"Tiết kiệm M2: **{r2['savings_pct']}%**. Cascade đóng góp lớn nhất vì model nhỏ có giá input/output thấp hơn. "
        "50% × 10% = 5% chỉ đúng cho phần input cache hoàn toàn; output vẫn tính đủ trước giảm batch. "
        "Batch chỉ dành cho request chịu được chờ, không dùng cho chat cần phản hồi ngay.", "",
        "## Kiểm toán GPU và purchasing (Guide 4.3, 6.4)", "",
        "| GPU bị flag | Util | MFU | MBU | Chi phí on-demand/30 ngày |",
        "|---|---:|---:|---:|---:|"]
    for lie in r1["lies"]:
        lines.append(f"| {lie['gpu_id']} | {lie['gpu_util_pct']:.1f}% | {lie['mfu']:.3f} | {lie['mbu']:.3f} | ${num(cat[lie['gpu_type']]['on_demand_hr'])*720:.2f} |")
    fleet_daily = sum(num(cat[g['gpu_type']]['on_demand_hr'])*24 for g in r1['summary'])
    lines += ["", "gpu-h100-4 có util cao nhất. GPU vẫn có thể bận vì chờ bộ nhớ hoặc chạy kernel nhỏ, nên util cao chưa chắc tạo ra nhiều FLOPs. "
        "Cần profile thêm trước khi đổi cấu hình GPU.", "",
        f"Idle = ${r1['idle_waste_daily']:.2f}/ngày = ${r1['idle_waste_daily']*30:.2f}/tháng, "
        f"chiếm {r1['idle_waste_daily']/fleet_daily:.2%} chi phí on-demand toàn fleet telemetry (${fleet_daily:.2f}/ngày).", "",
        "| Job | GPU | Tier | On-demand USD/30 ngày | Optimized USD/30 ngày |",
        "|---|---|---|---:|---:|"]
    for j in r3['recommendations']:
        lines.append(f"| {j['job_id']} | {j['gpu_type']} | {j['tier']} | {j['on_demand']} | {j['optimized']} |")
    lines += ["", f"M3: ${r3['on_demand_monthly']:,} → ${r3['optimized_monthly']:,}, giảm {r3['savings_pct']}%. "
        "Spot dành cho job interruptible; effective hours gồm 3% checkpoint + rework kỳ vọng (0,05 lần/giờ × 0,5 giờ). "
        "Reserved theo policy 55% duty; khi tính cam kết thật phải trả cả giờ không sử dụng, xét thời hạn 1/3 năm. "
        "job-infer-search chạy 18h/ngày: cần so 24h phí reserved với 18h on-demand; job ngắn/nhu cầu chưa chắc chắn nên ưu tiên on-demand. "
        "Bảng gốc chưa tính đủ nghĩa vụ cam kết.", "",
        "## Phân bổ team (Guide 7.4)", "",
        "| Team | USD/ngày | Tỷ trọng |", "|---|---:|---:|"]
    for team, cost in sorted(r4['by_team_exact'].items(), key=lambda item: -item[1]):
        lines.append(f"| {team} | {cost:.2f} | {cost/stages['batch']:.2%} |")
    lines += ["", f"Assistant cao nhất. Tag coverage {r4['tag_coverage']:.1%} vượt gate 80%; chargeback ready = {r4['chargeback_ready']}. "
        "Trước khi thu phí thật, cần rà lại tag của các request chưa gắn đủ. FOCUS export là mẫu 50 request để minh họa cách chuẩn hóa dữ liệu đa cloud.", "",
        "## Extension 4 — Ngân sách reasoning", "",
        "| Nhóm | Request | Traffic | Token | USD/ngày | Tỷ trọng USD | Wh/ngày | Tỷ trọng Wh |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, g in budget['groups'].items():
        lines.append(f"| {name} | {g['requests']} | {g['requests']/2400:.2%} | {g['tokens']:,} | {g['usd']:.6f} | {g['usd']/budget['before_usd']:.2%} | {g['wh']:.3f} | {g['wh']/budget['before_wh']:.2%} |")
    reasoning_tokens = budget['groups']['reasoning']['tokens']
    lines += ["", f"Với cùng {reasoning_tokens:,} token reasoning, năng lượng thường = {s.wh_per_query(reasoning_tokens):.3f} Wh; "
        f"reasoning = {s.wh_per_query(reasoning_tokens,is_reasoning=True):.3f} Wh (hệ số giả định 80× của lab). "
        "USD cùng model/token/cache/batch bằng nhau do không có bảng phụ phí reasoning; không suy ra chi phí tăng 80×.", "",
        "| Chỉ số | Trước | Sau cap 10% |", "|---|---:|---:|",
        f"| Request reasoning | {budget['groups']['reasoning']['requests']} | {budget['after_reasoning_requests']} |",
        f"| USD/ngày | {budget['before_usd']:.6f} | {budget['after_usd']:.6f} |",
        f"| Wh/ngày | {budget['before_wh']:.3f} | {budget['after_wh']:.3f} |", "",
        f"Reasoning hiện chỉ chiếm {budget['groups']['reasoning']['requests']/2400:.2%} traffic, thấp hơn cap 10%, nên chưa có request nào bị cắt và savings bằng 0. "
        "Nếu traffic tăng vượt ngưỡng, có thể chỉ bật reasoning cho tác vụ có confidence thấp; khi đó cần A/B test chất lượng trước.", "",
        "## Extension 5 — Carbon-aware scheduling", "",
        "Chọn tất cả job interruptible=1, bao gồm dev/batch. Dùng ngày thực tế trong days, GPU-hours = hours_per_day × days × num_gpus; "
        "Wh = GPU-hours × watts catalog. Giữ nguyên công việc, chưa cộng checkpoint, PUE hay chi phí chuyển dữ liệu. "
        "Không cộng tiền điện vào hóa đơn GPU cloud vì có thể đã bao gồm.", "",
        "| Job | GPU-hours | Wh | us-east-1 gCO2e | europe-north1 gCO2e | Giảm gCO2e |",
        "|---|---:|---:|---:|---:|---:|"]
    for j in carbon['jobs']:
        lines.append(f"| {j['job_id']} | {j['gpu_hours']:.0f} | {j['wh']:.0f} | {j['before_g']:.2f} | {j['after_g']:.2f} | {j['before_g']-j['after_g']:.2f} |")
    lines += ["", "| Vùng | USD/kWh | gCO2e/kWh | Điện USD/cùng công việc | gCO2e/cùng công việc |",
        "|---|---:|---:|---:|---:|"]
    for region in carbon['regions']:
        lines.append(f"| {region['region']} | {region['price_kwh']:.3f} | {region['carbon_kwh']} | {region['electricity_usd']:.3f} | {region['carbon_g']:.2f} |")
    lines += ["", f"Tổng {carbon['total_wh']:,.0f} Wh: {carbon['before_g']:,.2f} → {carbon['after_g']:,.2f} gCO2e, "
        f"giảm {carbon['before_g']-carbon['after_g']:,.2f} gCO2e ({1-carbon['after_g']/carbon['before_g']:.2%}). "
        f"Sạch nhất: {carbon['cleanest']}; điện rẻ nhất: {carbon['cheapest']}. "
        "europe-north1 phù hợp khi ưu tiên CO2, còn us-east-wa rẻ nhất về điện. Training bất đồng bộ dễ chuyển vùng hơn inference, "
        "vì inference còn phụ thuộc latency, data residency và GPU availability.", "",
        "## Ba hành động ưu tiên", "",
        "1. Áp dụng cascade theo đánh giá chất lượng, cache prefix và batch cho tác vụ chịu chờ; theo dõi $/1M-token cùng latency/chất lượng.",
        "2. Tắt GPU idle, profile hai GPU bị flag; xác minh VRAM/throughput rồi mới right-size. Dùng spot + checkpoint cho job chịu gián đoạn; kiểm tra tổng cam kết reserved.",
        "3. Chuẩn hóa tag và reconcile hóa đơn theo team; cap reasoning theo confidence sau A/B test và chuyển training phù hợp sang vùng sạch hơn."]
    # Preserve machine-readable evidence, independent from rounded terminal output.
    (out / 'extension_results.json').write_text(json.dumps(dict(M2=r2, carbon=carbon), indent=2), encoding='utf-8')
    tables = {}
    for filename in ('price_catalog.csv','gpu_telemetry.csv','token_usage.csv','workloads.csv'):
        df = pd.read_csv(Path(ROOT) / 'data' / filename)
        tables[filename] = dict(rows=len(df), columns=list(df.columns), missing=df.isna().sum().to_dict())
    (out / 'data_summary.json').write_text(json.dumps(tables, indent=2), encoding='utf-8')
    writeup = f"""# Bài viết ngắn — GPU FinOps tại NimbusAI

**Lê Phan Việt Cường — 2A202602641**

## Chi phí trước và sau

Với dữ liệu seed=25, hệ thống xử lý 2.400 request, tương đương {r2['total_tokens']:,} token mỗi ngày.
Nếu mọi request đều dùng model lớn và không dùng cache hay batch, chi phí là ${stages['baseline']:.2f}/ngày,
tức ${r2['baseline_per_m']:.3f}/1M-token. Sau khi áp dụng cascade, prompt cache và batch, chi phí còn
${stages['batch']:.2f}/ngày (${r2['optimized_per_m']:.3f}/1M-token), giảm {r2['savings_pct']}%.

Cascade đóng góp lớn nhất: nó giảm ${stages['baseline']-stages['cascade']:.2f}/ngày vì nhiều request được chuyển sang model nhỏ.
Cache giảm thêm ${stages['cascade']-stages['cache']:.2f}/ngày và batch giảm thêm ${stages['cache']-stages['batch']:.2f}/ngày.
Cache chỉ giảm phần input đã lưu, còn batch phù hợp với tác vụ không cần phản hồi ngay. Trước khi triển khai, tôi sẽ kiểm tra
chất lượng của policy cascade để tránh giảm chi phí nhưng làm câu trả lời kém đi.

Ở M3, policy spot/reserved giảm chi phí từ ${r3['on_demand_monthly']:,} xuống ${r3['optimized_monthly']:,}/tháng,
tương đương {r3['savings_pct']}%. Báo cáo M5 đưa ra kịch bản tổng ${baseline:,.0f} → ${optimized:,.0f}, giảm
{(1-optimized/baseline)*100:.1f}%. Đây là ước tính theo dữ liệu lab; cần đối chiếu lại với hóa đơn và nhu cầu thực tế trước khi cam kết reserved.

## GPU-Util và phân bổ trách nhiệm

gpu-h100-4 có GPU-Util 98,2% nhưng MFU chỉ 0,194; gpu-a10g-1 cũng bị flag. Điều này cho thấy GPU đang bận
nhưng không đạt nhiều FLOPs hữu ích, có thể vì chờ bộ nhớ hoặc do kernel nhỏ. Tôi sẽ tắt các GPU idle trước;
hiện idle cost là $20/ngày, tương đương $600/tháng. Với hai GPU bị flag, cần profile rồi mới quyết định right-size.

Team Assistant có chi phí inference cao nhất, ${r4['by_team']['assistant']:.2f}/ngày. Tag coverage {r4['tag_coverage']:.1%}
đã vượt gate 80%, nên có thể bắt đầu chargeback sau khi rà lại những request chưa gắn tag. File FOCUS export là mẫu
50 request, phục vụ việc chuẩn hóa dữ liệu chi phí giữa các cloud.

## Hai phần mở rộng và kết quả

**Reasoning budget:** reasoning có {budget['groups']['reasoning']['requests']} request, chiếm
{budget['groups']['reasoning']['requests']/2400:.2%} traffic nhưng chiếm {budget['groups']['reasoning']['wh']/budget['before_wh']:.2%} năng lượng.
Lý do là mô hình lab giả định reasoning tốn điện gấp 80 lần request thường. Traffic reasoning hiện dưới cap 10%,
nên cap chưa làm thay đổi chi phí hay năng lượng. Nếu tỷ lệ này tăng, tôi sẽ chỉ bật reasoning cho tác vụ có confidence thấp
và kiểm tra chất lượng qua A/B test.

**Carbon-aware scheduling:** các job interruptible tiêu thụ khoảng {carbon['total_wh']/1000:,.0f} kWh theo công suất catalog.
Nếu chuyển từ us-east-1 sang europe-north1, phát thải giảm từ {carbon['before_g']/1000:,.2f} xuống
{carbon['after_g']/1000:,.2f} kgCO2e, tức giảm {1-carbon['after_g']/carbon['before_g']:.2%}. europe-north1 sạch nhất,
còn us-east-wa rẻ nhất về điện. Vì training có thể chờ, đây là nhóm phù hợp nhất để chuyển vùng; inference cần cân nhắc latency
và nơi lưu dữ liệu trước.

## Ba việc làm đầu tiên

1. Kiểm tra chất lượng cascade, sau đó áp dụng cache và batch cho traffic phù hợp.
2. Tắt GPU idle, profile GPU bị flag, và chỉ mua reserved khi nhu cầu đủ ổn định.
3. Hoàn thiện tag, theo dõi reasoning, rồi chuyển các job training chịu chờ sang vùng sạch hơn.

Toàn bộ số liệu có thể tái tạo bằng `python missions/run_all.py`. Giá và carbon là dữ liệu minh họa của lab.
"""
    (out / 'writeup.md').write_text(writeup, encoding='utf-8')
    return '\n'.join(lines)
