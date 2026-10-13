# NimbusAI — GPU Cost Optimization Report

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,626  
**Projected savings:** $12,507  (**46%**)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

## Sustainability

- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e
- Cleanest region: europe-north1

_Figures are June-2026 as-of snapshots; re-baseline before acting._

## Phạm vi và phương pháp

Dữ liệu tổng hợp seed=25; giá là snapshot minh họa tháng 6/2026 của lab, không phải giá thị trường hiện tại. M2 so cùng input + output token; cache không giảm giá output, batch giảm 50% cả hóa đơn. Thứ tự phân rã là cascade → cache → batch; đóng góp phụ thuộc thứ tự, không cộng các tỷ lệ tiết kiệm độc lập.

M3 và M5 quy đổi theo tháng 30 ngày. Tổng M5 là kịch bản của lab: dữ liệu chưa liên kết trực tiếp telemetry, workload và request nên cần kiểm tra lại trước khi dùng làm dự báo hóa đơn. Hai extension bên dưới được báo cáo riêng, không cộng vào tổng savings.

## Unit economics và breakdown inference (M2)

Cùng **7,533,027 token/ngày**, 2.400 request; lặp 30 ngày cho bảng tháng.

| Bước | USD/ngày | USD/30 ngày | $/1M-token | Tiết kiệm tăng thêm USD/ngày |
|---|---:|---:|---:|---:|
| baseline | 48.874161 | 1466.2248 | 6.487984 | 0.000000 |
| cascade | 11.475643 | 344.2693 | 1.523377 | 37.398518 |
| cache | 10.279188 | 308.3756 | 1.364549 | 1.196455 |
| batch | 8.484623 | 254.5387 | 1.126323 | 1.794565 |

Tiết kiệm M2: **82.6%**. Cascade đóng góp lớn nhất vì model nhỏ có giá input/output thấp hơn. 50% × 10% = 5% chỉ đúng cho phần input cache hoàn toàn; output vẫn tính đủ trước giảm batch. Batch chỉ dành cho request chịu được chờ, không dùng cho chat cần phản hồi ngay.

## Kiểm toán GPU và purchasing (Guide 4.3, 6.4)

| GPU bị flag | Util | MFU | MBU | Chi phí on-demand/30 ngày |
|---|---:|---:|---:|---:|
| gpu-h100-4 | 98.2% | 0.194 | 0.207 | $1800.00 |
| gpu-a10g-1 | 96.9% | 0.268 | 0.302 | $720.00 |

gpu-h100-4 có util cao nhất. GPU vẫn có thể bận vì chờ bộ nhớ hoặc chạy kernel nhỏ, nên util cao chưa chắc tạo ra nhiều FLOPs. Cần profile thêm trước khi đổi cấu hình GPU.

Idle = $20.00/ngày = $600.00/tháng, chiếm 3.90% chi phí on-demand toàn fleet telemetry ($513.12/ngày).

| Job | GPU | Tier | On-demand USD/30 ngày | Optimized USD/30 ngày |
|---|---|---|---:|---:|
| job-train-llm | H100 | spot | 12000 | 7596 |
| job-train-embed | A100 | spot | 2148 | 1393 |
| job-finetune | H100 | spot | 900 | 570 |
| job-infer-chat | A10G | reserved | 4320 | 2592 |
| job-infer-rag | A100 | reserved | 3866 | 2160 |
| job-infer-search | L4 | reserved | 1728 | 972 |
| job-dev-sandbox | A10G | spot | 480 | 203 |
| job-batch-eval | H100 | spot | 225 | 142 |

M3: $25,667 → $15,627, giảm 39.1%. Spot dành cho job interruptible; effective hours gồm 3% checkpoint + rework kỳ vọng (0,05 lần/giờ × 0,5 giờ). Reserved theo policy 55% duty; khi tính cam kết thật phải trả cả giờ không sử dụng, xét thời hạn 1/3 năm. job-infer-search chạy 18h/ngày: cần so 24h phí reserved với 18h on-demand; job ngắn/nhu cầu chưa chắc chắn nên ưu tiên on-demand. Bảng gốc chưa tính đủ nghĩa vụ cam kết.

## Phân bổ team (Guide 7.4)

| Team | USD/ngày | Tỷ trọng |
|---|---:|---:|
| assistant | 2.59 | 30.55% |
| search | 2.49 | 29.39% |
| eval | 1.79 | 21.15% |
| rag | 1.60 | 18.91% |

Assistant cao nhất. Tag coverage 91.8% vượt gate 80%; chargeback ready = True. Trước khi thu phí thật, cần rà lại tag của các request chưa gắn đủ. FOCUS export là mẫu 50 request để minh họa cách chuẩn hóa dữ liệu đa cloud.

## Extension 4 — Ngân sách reasoning

| Nhóm | Request | Traffic | Token | USD/ngày | Tỷ trọng USD | Wh/ngày | Tỷ trọng Wh |
|---|---:|---:|---:|---:|---:|---:|---:|
| reasoning | 201 | 8.38% | 1,241,156 | 1.396464 | 16.46% | 29787.744 | 94.04% |
| standard | 2199 | 91.62% | 6,291,871 | 7.088159 | 83.54% | 1887.561 | 5.96% |

Với cùng 1,241,156 token reasoning, năng lượng thường = 372.347 Wh; reasoning = 29787.744 Wh (hệ số giả định 80× của lab). USD cùng model/token/cache/batch bằng nhau do không có bảng phụ phí reasoning; không suy ra chi phí tăng 80×.

| Chỉ số | Trước | Sau cap 10% |
|---|---:|---:|
| Request reasoning | 201 | 201 |
| USD/ngày | 8.484623 | 8.484623 |
| Wh/ngày | 31675.305 | 31675.305 |

Reasoning hiện chỉ chiếm 8.38% traffic, thấp hơn cap 10%, nên chưa có request nào bị cắt và savings bằng 0. Nếu traffic tăng vượt ngưỡng, có thể chỉ bật reasoning cho tác vụ có confidence thấp; khi đó cần A/B test chất lượng trước.

## Extension 5 — Carbon-aware scheduling

Chọn tất cả job interruptible=1, bao gồm dev/batch. Dùng ngày thực tế trong days, GPU-hours = hours_per_day × days × num_gpus; Wh = GPU-hours × watts catalog. Giữ nguyên công việc, chưa cộng checkpoint, PUE hay chi phí chuyển dữ liệu. Không cộng tiền điện vào hóa đơn GPU cloud vì có thể đã bao gồm.

| Job | GPU-hours | Wh | us-east-1 gCO2e | europe-north1 gCO2e | Giảm gCO2e |
|---|---:|---:|---:|---:|---:|
| job-train-llm | 2240 | 1568000 | 595840.00 | 47040.00 | 548800.00 |
| job-train-embed | 200 | 80000 | 30400.00 | 2400.00 | 28000.00 |
| job-finetune | 36 | 25200 | 9576.00 | 756.00 | 8820.00 |
| job-dev-sandbox | 352 | 52800 | 20064.00 | 1584.00 | 18480.00 |
| job-batch-eval | 90 | 63000 | 23940.00 | 1890.00 | 22050.00 |

| Vùng | USD/kWh | gCO2e/kWh | Điện USD/cùng công việc | gCO2e/cùng công việc |
|---|---:|---:|---:|---:|
| us-east-1 | 0.120 | 380 | 214.680 | 679820.00 |
| us-west-2 | 0.070 | 120 | 125.230 | 214680.00 |
| europe-north1 | 0.090 | 30 | 161.010 | 53670.00 |
| europe-central2 | 0.180 | 660 | 322.020 | 1180740.00 |
| us-east-wa | 0.055 | 90 | 98.395 | 161010.00 |

Tổng 1,789,000 Wh: 679,820.00 → 53,670.00 gCO2e, giảm 626,150.00 gCO2e (92.11%). Sạch nhất: europe-north1; điện rẻ nhất: us-east-wa. europe-north1 phù hợp khi ưu tiên CO2, còn us-east-wa rẻ nhất về điện. Training bất đồng bộ dễ chuyển vùng hơn inference, vì inference còn phụ thuộc latency, data residency và GPU availability.

## Ba hành động ưu tiên

1. Áp dụng cascade theo đánh giá chất lượng, cache prefix và batch cho tác vụ chịu chờ; theo dõi $/1M-token cùng latency/chất lượng.
2. Tắt GPU idle, profile hai GPU bị flag; xác minh VRAM/throughput rồi mới right-size. Dùng spot + checkpoint cho job chịu gián đoạn; kiểm tra tổng cam kết reserved.
3. Chuẩn hóa tag và reconcile hóa đơn theo team; cap reasoning theo confidence sau A/B test và chuyển training phù hợp sang vùng sạch hơn.