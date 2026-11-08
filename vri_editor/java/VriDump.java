import com.healthmarketscience.jackcess.Column;
import com.healthmarketscience.jackcess.DataType;
import com.healthmarketscience.jackcess.Database;
import com.healthmarketscience.jackcess.DatabaseBuilder;
import com.healthmarketscience.jackcess.Row;
import com.healthmarketscience.jackcess.Table;

import java.io.BufferedWriter;
import java.io.File;
import java.io.OutputStreamWriter;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Base64;
import java.util.Date;

/**
 * Reads one table with Jackcess (the same library that writes the file) and prints
 * it as TSV: a header row of column names, then one row per live record. Every cell
 * is Base64 encoded, so tabs and newlines in text cannot break the layout. Binary
 * and OLE columns are printed empty (mdb-export -b strip behaves the same way).
 */
public final class VriDump {
    private VriDump() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("usage: VriDump <mdb> <table>");
            System.exit(2);
        }
        Database db = DatabaseBuilder.open(new File(args[0]));
        try {
            Table table = db.getTable(args[1]);
            BufferedWriter out = new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8));
            StringBuilder header = new StringBuilder();
            for (Column column : table.getColumns()) {
                if (header.length() > 0) {
                    header.append('\t');
                }
                header.append(encode(column.getName()));
            }
            out.write(header.toString());
            out.write('\n');
            SimpleDateFormat fmt = new SimpleDateFormat("MM/dd/yy HH:mm:ss");
            for (Row row : table) {
                StringBuilder line = new StringBuilder();
                boolean first = true;
                for (Column column : table.getColumns()) {
                    if (!first) {
                        line.append('\t');
                    }
                    first = false;
                    line.append(encode(cell(row.get(column.getName()), column, fmt)));
                }
                out.write(line.toString());
                out.write('\n');
            }
            out.flush();
        } finally {
            db.close();
        }
    }

    private static String cell(Object value, Column column, SimpleDateFormat fmt) {
        if (value == null) {
            return "";
        }
        if (column.getType() == DataType.OLE || column.getType() == DataType.BINARY) {
            return "";
        }
        if (value instanceof Date) {
            return fmt.format((Date) value);
        }
        if (value instanceof java.time.LocalDateTime) {
            return ((java.time.LocalDateTime) value).format(
                    java.time.format.DateTimeFormatter.ofPattern("MM/dd/yy HH:mm:ss"));
        }
        if (value instanceof java.time.LocalDate) {
            return ((java.time.LocalDate) value).format(
                    java.time.format.DateTimeFormatter.ofPattern("MM/dd/yy")) + " 00:00:00";
        }
        if (value instanceof Boolean) {
            return ((Boolean) value) ? "-1" : "0";
        }
        if (value instanceof Double || value instanceof Float) {
            return new BigDecimal(value.toString()).round(new java.math.MathContext(15))
                    .stripTrailingZeros().toPlainString();
        }
        return value.toString();
    }

    private static String encode(String text) {
        return Base64.getEncoder().encodeToString(text.getBytes(StandardCharsets.UTF_8));
    }
}
