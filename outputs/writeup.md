# Bài viết ngắn — GPU FinOps tại NimbusAI

**Lê Phan Việt Cường — 2A202602641**

## Chi phí trước và sau

Với dữ liệu seed=25, hệ thống xử lý 2.400 request, tương đương 7,533,027 token mỗi ngày.
Nếu mọi request đều dùng model lớn và không dùng cache hay batch, chi phí là $48.87/ngày,
tức $6.488/1M-token. Sau khi áp dụng cascade, prompt cache và batch, chi phí còn
$8.48/ngày ($1.126/1M-token), giảm 82.6%.

Cascade đóng góp lớn nhất: nó giảm $37.40/ngày vì nhiều request được chuyển sang model nhỏ.
Cache giảm thêm $1.20/ngày và batch giảm thêm $1.79/ngày.
Cache chỉ giảm phần input đã lưu, còn batch phù hợp với tác vụ không cần phản hồi ngay. Trước khi triển khai, tôi sẽ kiểm tra
chất lượng của policy cascade để tránh giảm chi phí nhưng làm câu trả lời kém đi.

Ở M3, policy spot/reserved giảm chi phí từ $25,667 xuống $15,627/tháng,
tương đương 39.1%. Báo cáo M5 đưa ra kịch bản tổng $27,133 → $14,626, giảm
46.1%. Đây là ước tính theo dữ liệu lab; cần đối chiếu lại với hóa đơn và nhu cầu thực tế trước khi cam kết reserved.

## GPU-Util và phân bổ trách nhiệm

gpu-h100-4 có GPU-Util 98,2% nhưng MFU chỉ 0,194; gpu-a10g-1 cũng bị flag. Điều này cho thấy GPU đang bận
nhưng không đạt nhiều FLOPs hữu ích, có thể vì chờ bộ nhớ hoặc do kernel nhỏ. Tôi sẽ tắt các GPU idle trước;
hiện idle cost là $20/ngày, tương đương $600/tháng. Với hai GPU bị flag, cần profile rồi mới quyết định right-size.

Team Assistant có chi phí inference cao nhất, $2.59/ngày. Tag coverage 91.8%
đã vượt gate 80%, nên có thể bắt đầu chargeback sau khi rà lại những request chưa gắn tag. File FOCUS export là mẫu
50 request, phục vụ việc chuẩn hóa dữ liệu chi phí giữa các cloud.

## Hai phần mở rộng và kết quả

**Reasoning budget:** reasoning có 201 request, chiếm
8.38% traffic nhưng chiếm 94.04% năng lượng.
Lý do là mô hình lab giả định reasoning tốn điện gấp 80 lần request thường. Traffic reasoning hiện dưới cap 10%,
nên cap chưa làm thay đổi chi phí hay năng lượng. Nếu tỷ lệ này tăng, tôi sẽ chỉ bật reasoning cho tác vụ có confidence thấp
và kiểm tra chất lượng qua A/B test.

**Carbon-aware scheduling:** các job interruptible tiêu thụ khoảng 1,789 kWh theo công suất catalog.
Nếu chuyển từ us-east-1 sang europe-north1, phát thải giảm từ 679.82 xuống
53.67 kgCO2e, tức giảm 92.11%. europe-north1 sạch nhất,
còn us-east-wa rẻ nhất về điện. Vì training có thể chờ, đây là nhóm phù hợp nhất để chuyển vùng; inference cần cân nhắc latency
và nơi lưu dữ liệu trước.

## Ba việc làm đầu tiên

1. Kiểm tra chất lượng cascade, sau đó áp dụng cache và batch cho traffic phù hợp.
2. Tắt GPU idle, profile GPU bị flag, và chỉ mua reserved khi nhu cầu đủ ổn định.
3. Hoàn thiện tag, theo dõi reasoning, rồi chuyển các job training chịu chờ sang vùng sạch hơn.

Toàn bộ số liệu có thể tái tạo bằng `python missions/run_all.py`. Giá và carbon là dữ liệu minh họa của lab.
