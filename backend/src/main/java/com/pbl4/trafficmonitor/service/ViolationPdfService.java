package com.pbl4.trafficmonitor.service;

import com.lowagie.text.Document;
import com.lowagie.text.Element;
import com.lowagie.text.Font;
import com.lowagie.text.Image;
import com.lowagie.text.PageSize;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Phrase;
import com.lowagie.text.Rectangle;
import com.lowagie.text.pdf.BaseFont;
import com.lowagie.text.pdf.PdfPCell;
import com.lowagie.text.pdf.PdfPTable;
import com.lowagie.text.pdf.PdfWriter;
import com.pbl4.trafficmonitor.entity.Violation;
import com.pbl4.trafficmonitor.enums.ViolationType;
import com.pbl4.trafficmonitor.repository.ViolationRepository;
import com.pbl4.trafficmonitor.util.PenaltyRuleHelper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

/**
 * C3: Sinh biên bản xử phạt vi phạm hành chính dạng PDF.
 *
 * Vì sao làm ở backend thay vì frontend:
 *  - Cần nhúng font Unicode để hiển thị đúng tiếng Việt (dấu) và ảnh bằng chứng;
 *  - File PDF tải về trực tiếp, không phụ thuộc hộp thoại in của trình duyệt;
 *  - Nội dung lấy từ DB (nguồn chân lý), không phải dữ liệu đang hiển thị trên UI.
 *
 * Font Roboto (giấy phép Apache 2.0, hỗ trợ đầy đủ tiếng Việt) được nhúng sẵn
 * trong resources/fonts nên chạy offline vẫn đúng dấu.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class ViolationPdfService {

    private final ViolationRepository violationRepo;
    private final ImageStorageService imageStorageService;

    private static final String FONT_REGULAR_PATH = "/fonts/Roboto-Regular.ttf";
    private static final String FONT_BOLD_PATH = "/fonts/Roboto-Bold.ttf";

    private static final Color COLOR_PRIMARY = new Color(15, 23, 42);
    private static final Color COLOR_MUTED = new Color(100, 116, 139);
    private static final Color COLOR_DANGER = new Color(190, 18, 60);
    private static final Color COLOR_BORDER = new Color(203, 213, 225);
    private static final Color COLOR_DANGER_BG = new Color(255, 241, 242);

    /**
     * Trả về nội dung file PDF cho một biên bản.
     * @throws RuntimeException nếu không tìm thấy vi phạm (GlobalExceptionHandler sẽ đổi thành 400)
     */
    @Transactional(readOnly = true)
    public byte[] buildPdf(Long violationId) {
        Violation v = violationRepo.findById(violationId)
                .orElseThrow(() -> new RuntimeException("Không tìm thấy vi phạm ID: " + violationId));

        PenaltyRuleHelper.PenaltyInfo penalty = PenaltyRuleHelper.calculatePenalty(
                v.getViolationType(), v.getVehicleType());

        BaseFont regular = loadBaseFont(FONT_REGULAR_PATH);
        BaseFont bold = loadBaseFont(FONT_BOLD_PATH);

        Font fBody = new Font(regular, 10.5f, Font.NORMAL, COLOR_PRIMARY);
        Font fBodySmall = new Font(regular, 9f, Font.NORMAL, COLOR_MUTED);
        Font fBold = new Font(bold, 10.5f, Font.BOLD, COLOR_PRIMARY);
        Font fTitle = new Font(bold, 16f, Font.BOLD, COLOR_PRIMARY);
        Font fHeader = new Font(bold, 12.5f, Font.BOLD, COLOR_PRIMARY);
        Font fPenalty = new Font(bold, 13f, Font.BOLD, COLOR_DANGER);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Document doc = new Document(PageSize.A4, 42, 42, 30, 26);

        try {
            PdfWriter.getInstance(doc, out);
            doc.open();

            // ---------- Quốc hiệu ----------
            Paragraph quocHieu = new Paragraph("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", new Font(bold, 12.5f, Font.BOLD, COLOR_PRIMARY));
            quocHieu.setAlignment(Element.ALIGN_CENTER);
            doc.add(quocHieu);

            Paragraph tieuNgu = new Paragraph("Độc lập – Tự do – Hạnh phúc", new Font(bold, 12f, Font.BOLD, COLOR_PRIMARY));
            tieuNgu.setAlignment(Element.ALIGN_CENTER);
            tieuNgu.setSpacingAfter(2f);
            doc.add(tieuNgu);

            Paragraph line = new Paragraph("___________________", new Font(regular, 11f, Font.NORMAL, COLOR_MUTED));
            line.setAlignment(Element.ALIGN_CENTER);
            line.setSpacingAfter(8f);
            doc.add(line);

            // ---------- Tiêu đề ----------
            Paragraph title = new Paragraph("BIÊN BẢN XỬ PHẠT VI PHẠM HÀNH CHÍNH", fTitle);
            title.setAlignment(Element.ALIGN_CENTER);
            title.setSpacingAfter(1f);
            doc.add(title);

            Paragraph subTitle = new Paragraph("(Bản trích xuất tự động từ Hệ thống Giám sát Giao thông Thông minh PBL4)", fBodySmall);
            subTitle.setAlignment(Element.ALIGN_CENTER);
            subTitle.setSpacingAfter(2f);
            doc.add(subTitle);

            int year = v.getDetectedAt() != null ? v.getDetectedAt().getYear() : LocalDateTime.now().getYear();
            Paragraph soBienBan = new Paragraph("Số: BB-" + v.getId() + "/" + year + "/PBL4-TM", new Font(regular, 10f, Font.ITALIC, COLOR_MUTED));
            soBienBan.setAlignment(Element.ALIGN_RIGHT);
            soBienBan.setSpacingAfter(6f);
            doc.add(soBienBan);

            // ---------- Thông tin vi phạm ----------
            doc.add(sectionHeading("I. THÔNG TIN VỤ VI PHẠM", bold));

            String cameraName = v.getCamera() != null && v.getCamera().getName() != null
                    ? v.getCamera().getName() : "Camera giám sát";
            String cameraLocation = v.getCamera() != null && v.getCamera().getLocationDescription() != null
                    ? v.getCamera().getLocationDescription() : "Không xác định";

            PdfPTable info = new PdfPTable(new float[]{1.05f, 2.35f});
            info.setWidthPercentage(100);
            info.setSpacingAfter(6f);

            addInfoRow(info, "Thời điểm ghi nhận", formatTime(v.getDetectedAt()), regular, bold);
            addInfoRow(info, "Địa điểm", cameraName + " – " + cameraLocation, regular, bold);
            addInfoRow(info, "Phương tiện", vehicleLabel(v), regular, bold);
            addInfoRow(info, "Hành vi vi phạm", violationLabel(v.getViolationType()), regular, bold);
            addInfoRow(info, "Độ tin cậy AI", v.getConfidence() != null
                    ? String.format(Locale.US, "%.2f%%", v.getConfidence() * 100) : "Không có", regular, bold);
            addInfoRow(info, "Mã hồ sơ", "VPHC #" + v.getId(), regular, bold);
            addInfoRow(info, "Trạng thái hồ sơ", statusLabel(v), regular, bold);
            if (v.getConfirmedBy() != null) {
                addInfoRow(info, "Cán bộ xử lý", v.getConfirmedBy().getFullName(), regular, bold);
            }
            if (v.getConfirmedAt() != null) {
                addInfoRow(info, "Thời điểm duyệt", formatTime(v.getConfirmedAt()), regular, bold);
            }
            if (v.getNotes() != null && !v.getNotes().isBlank()) {
                addInfoRow(info, "Ghi chú của CSGT", v.getNotes(), regular, bold);
            }
            doc.add(info);

            // ---------- Ảnh bằng chứng ----------
            doc.add(sectionHeading("II. HÌNH ẢNH BẰNG CHỨNG", bold));
            byte[] imageBytes = loadEvidenceImage(v);
            if (imageBytes != null) {
                try {
                    Image img = Image.getInstance(imageBytes);
                    img.scaleToFit(470f, 205f);
                    img.setAlignment(Element.ALIGN_CENTER);
                    img.setSpacingAfter(2f);
                    doc.add(img);
                    Paragraph caption = new Paragraph(
                            "Ảnh do AI trích xuất tại thời điểm vi phạm, khung đỏ đánh dấu phương tiện.",
                            fBodySmall);
                    caption.setAlignment(Element.ALIGN_CENTER);
                    caption.setSpacingAfter(6f);
                    doc.add(caption);
                } catch (Exception e) {
                    log.warn("Không chèn được ảnh bằng chứng cho vi phạm #{}: {}", v.getId(), e.getMessage());
                    doc.add(noImageParagraph(fBody));
                }
            } else {
                doc.add(noImageParagraph(fBody));
            }

            // ---------- Mức phạt ----------
            doc.add(sectionHeading("III. MỨC PHẠT ĐỀ XUẤT", bold));

            PdfPTable penaltyTable = new PdfPTable(1);
            penaltyTable.setWidthPercentage(100);
            penaltyTable.setSpacingAfter(6f);

            PdfPCell penaltyCell = new PdfPCell();
            penaltyCell.setBackgroundColor(COLOR_DANGER_BG);
            penaltyCell.setBorderColor(new Color(254, 205, 211));
            penaltyCell.setPadding(10f);

            Paragraph fineP = new Paragraph(safe(penalty.getFineAmount()), fPenalty);
            fineP.setSpacingAfter(3f);
            penaltyCell.addElement(fineP);

            penaltyCell.addElement(new Paragraph("Căn cứ pháp lý: " + safe(penalty.getLegalBasis()), fBody));
            penaltyCell.addElement(new Paragraph(
                    penalty.getPenaltyPoints() != null && penalty.getPenaltyPoints() > 0
                            ? "Hình thức bổ sung: trừ " + penalty.getPenaltyPoints() + " điểm Giấy phép lái xe."
                            : "Hình thức bổ sung: không trừ điểm Giấy phép lái xe.",
                    fBody));
            penaltyTable.addCell(penaltyCell);
            doc.add(penaltyTable);

            Paragraph legalNote = new Paragraph(
                    "Mức phạt nêu trên được hệ thống tra cứu tự động theo Nghị định 168/2024/NĐ-CP. "
                            + "Biên bản này là bản trích xuất phục vụ công tác tham khảo, không thay thế "
                            + "biên bản xử phạt do cơ quan Công an lập theo mẫu quy định.",
                    new Font(regular, 8.5f, Font.ITALIC, COLOR_MUTED));
            legalNote.setSpacingAfter(8f);
            doc.add(legalNote);

            // ---------- Chữ ký ----------
            PdfPTable signTable = new PdfPTable(3);
            signTable.setWidthPercentage(100);
            signTable.setSpacingBefore(6f);

            String officerName = v.getConfirmedBy() != null ? v.getConfirmedBy().getFullName() : "(Ký, ghi rõ họ tên)";
            signTable.addCell(signCell("NGƯỜI LẬP BIÊN BẢN", "Hệ thống AI PBL4", regular, bold));
            signTable.addCell(signCell("CÁN BỘ XỬ LÝ", officerName, regular, bold));
            signTable.addCell(signCell("NGƯỜI VI PHẠM", "(Ký, ghi rõ họ tên)", regular, bold));
            doc.add(signTable);

            Paragraph footer = new Paragraph(
                    "Biên bản được tạo lúc " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss dd/MM/yyyy"))
                            + " · Hệ thống Giám sát Giao thông Thông minh PBL4 – Nhóm 3",
                    new Font(regular, 8f, Font.NORMAL, COLOR_MUTED));
            footer.setSpacingBefore(10f);
            footer.setAlignment(Element.ALIGN_CENTER);
            doc.add(footer);

            doc.close();
            return out.toByteArray();
        } catch (Exception e) {
            throw new RuntimeException("Không tạo được biên bản PDF: " + e.getMessage(), e);
        } finally {
            if (doc.isOpen()) {
                doc.close();
            }
        }
    }

    // ---------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------

    private BaseFont loadBaseFont(String classpathPath) {
        try (InputStream in = ViolationPdfService.class.getResourceAsStream(classpathPath)) {
            if (in == null) {
                throw new IllegalStateException("Thiếu file font " + classpathPath);
            }
            byte[] fontBytes = in.readAllBytes();
            String name = classpathPath.substring(classpathPath.lastIndexOf('/') + 1);
            return BaseFont.createFont(name, BaseFont.IDENTITY_H, BaseFont.EMBEDDED, true, fontBytes, null);
        } catch (Exception e) {
            log.error("Không nạp được font {} ({}). Chữ tiếng Việt có thể bị lỗi dấu.", classpathPath, e.getMessage());
            try {
                return BaseFont.createFont(BaseFont.HELVETICA, BaseFont.WINANSI, BaseFont.NOT_EMBEDDED);
            } catch (Exception fatal) {
                throw new RuntimeException("Không khởi tạo được font cho PDF", fatal);
            }
        }
    }

    private Paragraph sectionHeading(String text, BaseFont bold) {
        Paragraph p = new Paragraph(text, new Font(bold, 10.5f, Font.BOLD, COLOR_PRIMARY));
        p.setSpacingBefore(5f);
        p.setSpacingAfter(4f);
        return p;
    }

    private void addInfoRow(PdfPTable table, String label, String value, BaseFont regular, BaseFont bold) {
        PdfPCell labelCell = new PdfPCell(new Phrase(label, new Font(bold, 9f, Font.BOLD, COLOR_MUTED)));
        labelCell.setBorderColor(COLOR_BORDER);
        labelCell.setPadding(4f);
        table.addCell(labelCell);

        PdfPCell valueCell = new PdfPCell(new Phrase(safe(value), new Font(regular, 9.5f, Font.NORMAL, COLOR_PRIMARY)));
        valueCell.setBorderColor(COLOR_BORDER);
        valueCell.setPadding(4f);
        table.addCell(valueCell);
    }

    private PdfPCell signCell(String title, String name, BaseFont regular, BaseFont bold) {
        PdfPCell cell = new PdfPCell();
        cell.setBorder(Rectangle.NO_BORDER);
        cell.setPaddingTop(2f);
        cell.setPaddingBottom(14f);
        cell.setHorizontalAlignment(Element.ALIGN_CENTER);

        Paragraph pTitle = new Paragraph(title, new Font(bold, 9.5f, Font.BOLD, COLOR_PRIMARY));
        pTitle.setAlignment(Element.ALIGN_CENTER);
        pTitle.setSpacingAfter(2f);
        cell.addElement(pTitle);

        Paragraph pName = new Paragraph(safe(name), new Font(regular, 9.5f, Font.NORMAL, COLOR_MUTED));
        pName.setAlignment(Element.ALIGN_CENTER);
        cell.addElement(pName);

        Paragraph pSign = new Paragraph("......................", new Font(regular, 9.5f, Font.NORMAL, COLOR_MUTED));
        pSign.setAlignment(Element.ALIGN_CENTER);
        cell.addElement(pSign);
        return cell;
    }

    private Paragraph noImageParagraph(Font fBody) {
        Paragraph p = new Paragraph("(Không tải được ảnh bằng chứng cho hồ sơ này)", fBody);
        p.setAlignment(Element.ALIGN_CENTER);
        p.setSpacingAfter(10f);
        return p;
    }

    /** Ưu tiên đọc file trên ổ cứng, sau đó mới tải từ URL (Cloudinary / API ảnh nội bộ). */
    private byte[] loadEvidenceImage(Violation v) {
        String fileName = v.getEvidenceImagePath();
        if (fileName != null && !fileName.isBlank()) {
            try {
                byte[] local = imageStorageService.loadImage(fileName);
                if (local != null && local.length > 0) {
                    return local;
                }
            } catch (Exception e) {
                log.debug("Không đọc được ảnh local {}: {}", fileName, e.getMessage());
            }
        }

        String url = v.getEvidenceImageUrl();
        if (url == null || url.isBlank()) {
            return null;
        }
        try {
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(4))
                    .followRedirects(HttpClient.Redirect.NORMAL)
                    .build();
            HttpRequest request = HttpRequest.newBuilder(URI.create(url))
                    .timeout(Duration.ofSeconds(6))
                    .GET()
                    .build();
            HttpResponse<byte[]> response = client.send(request, HttpResponse.BodyHandlers.ofByteArray());
            if (response.statusCode() == 200 && response.body().length > 0) {
                return response.body();
            }
            log.warn("Tải ảnh bằng chứng thất bại (HTTP {}) cho vi phạm #{}", response.statusCode(), v.getId());
        } catch (Exception e) {
            log.warn("Lỗi tải ảnh bằng chứng cho vi phạm #{}: {}", v.getId(), e.getMessage());
        }
        return null;
    }

    private String formatTime(LocalDateTime time) {
        return time == null ? "Không xác định"
                : time.format(DateTimeFormatter.ofPattern("'ngày' dd 'tháng' MM 'năm' yyyy, HH:mm:ss"));
    }

    private String vehicleLabel(Violation v) {
        if (v.getVehicleType() == null) {
            return "Chưa xác định";
        }
        return switch (v.getVehicleType()) {
            case MOTORCYCLE -> "Xe mô tô / xe gắn máy";
            case CAR -> "Ô tô con";
            case TRUCK -> "Xe tải";
            case BUS -> "Xe khách / xe buýt";
            case UNKNOWN -> "Chưa xác định";
        };
    }

    private String violationLabel(ViolationType type) {
        if (type == null) {
            return "Chưa xác định";
        }
        return switch (type) {
            case NO_HELMET -> "Không đội mũ bảo hiểm khi điều khiển xe mô tô / xe gắn máy";
            case RED_LIGHT_CROSS -> "Không chấp hành hiệu lệnh của đèn tín hiệu giao thông (vượt đèn đỏ)";
        };
    }

    private String statusLabel(Violation v) {
        if (v.getStatus() == null) {
            return "Chờ duyệt";
        }
        return switch (v.getStatus()) {
            case PENDING -> "Chờ duyệt";
            case CONFIRMED -> "Đã xác nhận xử phạt";
            case DISMISSED -> "Đã bác bỏ (báo giả)";
        };
    }

    private String safe(String value) {
        return value == null || value.isBlank() ? "—" : value;
    }
}
