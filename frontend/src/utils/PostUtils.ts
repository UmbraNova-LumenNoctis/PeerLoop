export const timeFormat = (dateString: string): string => {
    const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

    const now: Date = new Date();
    const date: Date = new Date(dateString);
    const seconds: number = Math.floor((now.getTime() - date.getTime()) / 1000);

    const intervals: { unit: string, seconds: number }[] = [
        { unit: "year", seconds: 31536000 },
        { unit: "month", seconds: 2592000 },
        { unit: "week", seconds: 604800 },
        { unit: "day", seconds: 86400 },
        { unit: "hour", seconds: 3600 },
        { unit: "minute", seconds: 60 },
        { unit: "second", seconds: 1 }
    ];

    for (const interval of intervals) {
        const value: number = Math.floor(seconds / interval.seconds);

        if (value >= 1)
            return rtf.format(-value, interval.unit as Intl.RelativeTimeFormatUnit);
    }

    return ("just now");
}
