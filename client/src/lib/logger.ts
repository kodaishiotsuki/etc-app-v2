import pino from "pino";

const isDevelopment = process.env.NODE_ENV === "development";

const logger = pino({
  level: isDevelopment ? "debug" : "error",
  enabled: isDevelopment,
  transport: isDevelopment
    ? {
        target: "pino-pretty",
        options: {
          colorize: true,
          translateTime: "SYS:standard",
        },
      }
    : undefined,
});

type LogArgs = Parameters<typeof logger.debug>;

export const log = {
  debug: (...args: LogArgs) => logger.debug(...args),
  info: (...args: LogArgs) => logger.info(...args),
  warn: (...args: LogArgs) => logger.warn(...args),
  error: (...args: LogArgs) => logger.error(...args),
};
