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
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class VriWriteback {
    private VriWriteback() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("usage: VriWriteback <mdb> <updates.tsv>");
            System.exit(2);
        }
        Path dbPath = Paths.get(args[0]);
        Path updatesPath = Paths.get(args[1]);
        Database db = DatabaseBuilder.open(new File(dbPath.toString()));
        int updated = 0;
        try {
            Table vcpe = db.getTable("VEGETATION_COVER_POLYGON_EST");
            Table tcl = db.getTable("TREE_COVER_LAYER_ESTIMATED");
            Table lcc = db.getTable("LAND_COVER_COMPONENT_EST");
            try (BufferedReader reader = Files.newBufferedReader(updatesPath, StandardCharsets.UTF_8)) {
                String line;
                while ((line = reader.readLine()) != null) {
                    if (line.isEmpty() || line.startsWith("#")) {
                        continue;
                    }
                    String[] fields = line.split("\t", -1);
                    String kind = fields[0];
                    if ("VCPE".equals(kind) && fields.length >= 7) {
                        Map<String, Object> values = new LinkedHashMap<>();
                        for (int i = 0; i < 5; i++) {
                            values.put("BCLCS_LEVEL" + (i + 1) + "_CODE", nullOr(fields[2 + i]));
                        }
                        updated += updateByKey(vcpe, "FOREST_COVER_OBJECT_ID", fields[1], values);
                    } else if ("TCL".equals(kind) && fields.length >= 3) {
                        Map<String, Object> values = new LinkedHashMap<>();
                        values.put("FOREST_COVER_RANK_CODE", nullOr(fields[2]));
                        updated += updateByKey(tcl, "TREE_COVER_LAYER_ESTIMATED_ID", fields[1], values);
                    } else if ("LCC".equals(kind) && fields.length >= 3) {
                        Map<String, Object> values = new LinkedHashMap<>();
                        values.put("LAND_COVER_ORDER", fields[2].isEmpty() ? null : Integer.valueOf(fields[2]));
                        updated += updateByKey(lcc, "LAND_COVER_COMPONENT_EST_ID", fields[1], values);
                    } else {
                        throw new IllegalArgumentException("bad update line: " + line);
                    }
                }
            }
        } finally {
            db.close();
        }
        System.out.println("updated=" + updated);
    }

    private static String nullOr(String value) {
        if (value == null || value.isEmpty() || "\\N".equals(value)) {
            return null;
        }
        return value;
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
        return matches.size();
    }
}
