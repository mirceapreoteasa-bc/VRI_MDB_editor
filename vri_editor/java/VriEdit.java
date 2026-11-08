import com.healthmarketscience.jackcess.Column;
import com.healthmarketscience.jackcess.DataType;
import com.healthmarketscience.jackcess.Database;
import com.healthmarketscience.jackcess.DatabaseBuilder;
import com.healthmarketscience.jackcess.Row;
import com.healthmarketscience.jackcess.Table;

import java.io.BufferedReader;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Small one-shot editor for the VRI editor skeleton. */
public final class VriEdit {
    private VriEdit() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("usage: VriEdit <mdb> <edits.tsv>");
            System.exit(2);
        }
        Path dbPath = Paths.get(args[0]);
        Path editsPath = Paths.get(args[1]);
        Database db = DatabaseBuilder.open(new File(dbPath.toString()));
        int updated = 0;
        try (BufferedReader reader = Files.newBufferedReader(editsPath, StandardCharsets.UTF_8)) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                String[] parts = line.split("\t", -1);
                if (parts.length < 4) {
                    throw new IllegalArgumentException("bad edit line: " + line);
                }
                String action = parts[0];
                Table table = db.getTable(parts[1]);
                Map<String, Object> values = new LinkedHashMap<>();
                for (int i = 4; i < parts.length; i++) {
                    int eq = parts[i].indexOf('=');
                    if (eq < 0) {
                        throw new IllegalArgumentException("bad field: " + parts[i]);
                    }
                    String name = parts[i].substring(0, eq);
                    String encoded = parts[i].substring(eq + 1);
                    values.put(name, decode(table.getColumn(name), encoded));
                }
                if ("U".equals(action)) {
                    updated += updateByKey(table, parts[2], parts[3], values);
                } else if ("I".equals(action)) {
                    table.addRowFromMap(values);
                    updated++;
                } else if ("D".equals(action)) {
                    updated += deleteByKey(table, parts[2], parts[3]);
                } else {
                    throw new IllegalArgumentException("bad action: " + action);
                }
            }
        } finally {
            db.close();
        }
        System.out.println("updated=" + updated);
    }

    private static Object decode(Column column, String encoded) throws Exception {
        if ("~".equals(encoded)) {
            return null;
        }
        if (column.getType() == DataType.OLE || column.getType() == DataType.BINARY) {
            if (encoded.isEmpty()) {
                return null;
            }
            return Base64.getDecoder().decode(encoded);
        }
        String value = new String(Base64.getDecoder().decode(encoded), StandardCharsets.UTF_8);
        if (value.isEmpty()) {
            if (column.getType() == DataType.TEXT || column.getType() == DataType.MEMO) {
                return "";
            }
            return null;
        }
        switch (column.getType()) {
            case BYTE:
            case INT:
            case LONG:
                return Integer.valueOf(value);
            case DOUBLE:
            case FLOAT:
            case NUMERIC:
                return Double.valueOf(value);
            case BOOLEAN:
                return Boolean.valueOf(value);
            case SHORT_DATE_TIME:
                return parseDate(value);
            default:
                return value;
        }
    }

    private static java.util.Date parseDate(String value) throws Exception {
        for (String pattern : new String[]{
                "yyyy-MM-dd'T'HH:mm:ss", "yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd",
                "MM/dd/yy HH:mm:ss", "MM/dd/yyyy HH:mm:ss", "MM/dd/yy", "MM/dd/yyyy",
                "dd/MM/yyyy HH:mm:ss", "dd/MM/yyyy", "dd/MM/yy", "yyyy/MM/dd",
                "dd-MMM-yyyy", "MMM dd yyyy"}) {
            try {
                return new SimpleDateFormat(pattern).parse(value);
            } catch (java.text.ParseException ignored) {
                // try the next format
            }
        }
        throw new IllegalArgumentException("unsupported date: " + value);
    }

    private static int deleteByKey(Table table, String keyName, String wanted) throws Exception {
        List<Row> matches = new ArrayList<>();
        for (Row row : table) {
            Object value = row.get(keyName);
            if (value != null && String.valueOf(value).trim().equals(wanted)) {
                matches.add(row);
            }
        }
        for (Row row : matches) {
            table.deleteRow(row);
        }
        if (matches.isEmpty()) {
            throw new IllegalArgumentException(
                    "no row " + table.getName() + "." + keyName + "=" + wanted);
        }
        return matches.size();
    }

    private static int updateByKey(Table table, String keyName, String wanted,
                                   Map<String, Object> values) throws Exception {
        List<Row> matches = new ArrayList<>();
        for (Row row : table) {
            Object value = row.get(keyName);
            if (value != null && String.valueOf(value).trim().equals(wanted)) {
                matches.add(row);
            }
        }
        for (Row row : matches) {
            for (Map.Entry<String, Object> entry : values.entrySet()) {
                row.put(entry.getKey(), entry.getValue());
            }
            table.updateRow(row);
        }
        if (matches.isEmpty()) {
            throw new IllegalArgumentException(
                    "no row " + table.getName() + "." + keyName + "=" + wanted);
        }
        return matches.size();
    }
}
