import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** Independent exact-integer worker. No Ray native bindings or dependencies. */
public final class StatsWorker {
    private static long number(String token) {
        if (!token.matches("-?(0|[1-9][0-9]*)")) {
            throw new IllegalArgumentException();
        }
        return Long.parseLong(token);
    }

    public static void main(String[] args) throws IOException {
        try {
            byte[] bytes = System.in.readNBytes(65537);
            if (bytes.length > 65536) throw new IllegalArgumentException();
            for (byte b : bytes) {
                if (b < 0 || (b < 32 && b != 9 && b != 10 && b != 13)) {
                    throw new IllegalArgumentException();
                }
            }
            String[] tokens = new String(bytes, StandardCharsets.US_ASCII).trim().split("\\s+");
            if (tokens.length < 2 || !tokens[0].equals("RAYPOLY1")) {
                throw new IllegalArgumentException();
            }
            long n = number(tokens[1]);
            if (n < 0 || n > 4096 || tokens.length != n + 2) {
                throw new IllegalArgumentException();
            }
            long sum = 0;
            long squares = 0;
            for (int i = 2; i < tokens.length; i++) {
                long value = number(tokens[i]);
                if (value < -1000000 || value > 1000000) throw new IllegalArgumentException();
                sum += value;
                squares += value * value;
            }
            System.out.printf("{\"protocol\":\"RAYPOLY1\",\"language\":\"java\","
                + "\"count\":%d,\"sum\":%d,\"sum_squares\":%d}%n", n, sum, squares);
        } catch (IllegalArgumentException ex) {
            System.err.println("invalid request");
            System.exit(2);
        }
    }
}
