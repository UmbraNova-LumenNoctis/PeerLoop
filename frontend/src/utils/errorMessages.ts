interface ApiErrorFormatOptions {
    statusCode?: number | null;
    detail?: string | null;
    endpoint?: string | null;
}

export const ERROR_DICTIONARY: Record<string, string> = {
    // HTTP client errors (4xx)
    HTTP_400: "la requête est invalide.",
    HTTP_401: "vous devez vous connecter pour continuer.",
    HTTP_402: "le paiement est requis pour cette opération.",
    HTTP_403: "vous n'avez pas l'autorisation d'effectuer cette action.",
    HTTP_404: "la ressource demandée n'a pas été trouvée.",
    HTTP_405: "la méthode HTTP utilisée n'est pas autorisée.",
    HTTP_406: "le format de réponse demandé n'est pas disponible.",
    HTTP_407: "une authentification proxy est requise.",
    HTTP_408: "la requête a expiré.",
    HTTP_409: "un conflit a été détecté avec les données existantes.",
    HTTP_410: "la ressource demandée n'est plus disponible.",
    HTTP_411: "la longueur de la requête est requise.",
    HTTP_412: "une précondition de requête a échoué.",
    HTTP_413: "la requête est trop volumineuse.",
    HTTP_414: "l'URL demandée est trop longue.",
    HTTP_415: "le type de contenu envoyé n'est pas supporté.",
    HTTP_416: "la plage demandée n'est pas satisfaisable.",
    HTTP_417: "l'attente indiquée par la requête ne peut pas être satisfaite.",
    HTTP_418: "la requête ne peut pas être traitée sur cette ressource.",
    HTTP_421: "la requête a été envoyée au mauvais serveur.",
    HTTP_422: "certaines données sont invalides. Vérifiez les champs saisis.",
    HTTP_423: "la ressource est verrouillée.",
    HTTP_424: "la requête dépend d'une action qui a échoué.",
    HTTP_425: "la requête a été rejetée car trop anticipée.",
    HTTP_426: "une mise à jour du protocole est requise.",
    HTTP_428: "une condition est requise pour traiter cette requête.",
    HTTP_429: "trop de requêtes ont été envoyées. Merci de réessayer dans un instant.",
    HTTP_431: "les en-têtes HTTP sont trop volumineux.",
    HTTP_451: "la ressource n'est pas accessible pour des raisons légales.",

    // HTTP server errors (5xx)
    HTTP_500: "une erreur interne est survenue côté serveur.",
    HTTP_501: "cette fonctionnalité n'est pas implémentée côté serveur.",
    HTTP_502: "le service est momentanément indisponible.",
    HTTP_503: "le service est temporairement indisponible.",
    HTTP_504: "le service met trop de temps à répondre.",
    HTTP_505: "la version HTTP n'est pas supportée par le serveur.",
    HTTP_506: "une erreur de négociation de contenu est survenue côté serveur.",
    HTTP_507: "espace de stockage insuffisant côté serveur.",
    HTTP_508: "une boucle a été détectée pendant le traitement serveur.",
    HTTP_510: "des extensions HTTP requises sont manquantes.",
    HTTP_511: "une authentification réseau est requise.",

    // Generic families
    HTTP_4XX_GENERIC: "la requête a été refusée par le serveur.",
    HTTP_5XX_GENERIC: "une erreur serveur est survenue.",

    // Network / transport / runtime
    NETWORK_ERROR: "impossible de contacter le serveur. Vérifiez votre connexion.",
    NETWORK_TIMEOUT: "le serveur met trop de temps à répondre.",
    REQUEST_ABORTED: "la requête a été interrompue avant la réponse.",
    REQUEST_CANCELED: "la requête a été annulée.",
    DNS_RESOLUTION_FAILED: "le nom du serveur n'a pas pu être résolu.",
    SSL_ERROR: "une erreur TLS/SSL est survenue pendant la connexion sécurisée.",
    CORS_BLOCKED: "la requête a été bloquée par la politique de sécurité du navigateur (CORS).",
    OFFLINE: "vous semblez hors ligne. Vérifiez votre connexion Internet.",

    // Domain-specific explicit errors
    USER_NOT_FOUND: "l'utilisateur n'a pas été trouvé.",
    USER_ALREADY_EXISTS: "l'utilisateur existe déjà.",
    EMAIL_ALREADY_EXISTS: "cet email est déjà utilisé.",
    PSEUDO_ALREADY_EXISTS: "ce pseudo est déjà utilisé.",
    PHONE_ALREADY_EXISTS: "ce numéro de téléphone est déjà utilisé.",
    INVALID_CREDENTIALS: "email, pseudo ou mot de passe invalide.",
    INVALID_TOKEN: "le jeton d'authentification est invalide.",
    MISSING_TOKEN: "aucun jeton d'authentification n'a été fourni.",
    TOKEN_EXPIRED: "votre session a expiré. Merci de vous reconnecter.",
    SESSION_EXPIRED: "votre session a expiré. Merci de vous reconnecter.",
    ACCOUNT_DISABLED: "votre compte est désactivé.",
    ACCOUNT_LOCKED: "votre compte est temporairement verrouillé.",
    EMAIL_NOT_CONFIRMED: "votre adresse email n'est pas encore confirmée.",
    TWO_FA_REQUIRED: "une vérification 2FA est requise pour continuer.",
    TWO_FA_INVALID_CODE: "le code 2FA saisi est invalide.",

    VALIDATION_ERROR: "les données envoyées sont invalides.",
    REQUIRED_FIELD_MISSING: "un ou plusieurs champs obligatoires sont manquants.",
    INVALID_EMAIL_FORMAT: "le format de l'email est invalide.",
    INVALID_PASSWORD_FORMAT: "le mot de passe ne respecte pas les règles demandées.",
    INVALID_FILE_TYPE: "le type de fichier n'est pas autorisé.",
    FILE_TOO_LARGE: "le fichier est trop volumineux.",

    CONVERSATION_NOT_FOUND: "la conversation demandée n'a pas été trouvée.",
    MESSAGE_NOT_FOUND: "le message demandé n'a pas été trouvé.",
    FRIENDSHIP_NOT_FOUND: "la relation d'amitié n'a pas été trouvée.",
    FRIEND_REQUEST_ALREADY_SENT: "une demande d'amitié a déjà été envoyée.",
    FRIENDSHIP_ALREADY_EXISTS: "vous êtes déjà ami avec cet utilisateur.",
    NOTIFICATION_NOT_FOUND: "la notification demandée n'a pas été trouvée.",
    POST_NOT_FOUND: "le post demandé n'a pas été trouvé.",
    COMMENT_NOT_FOUND: "le commentaire demandé n'a pas été trouvé.",
    RESOURCE_DELETED: "la ressource demandée a été supprimée.",
    RATE_LIMIT_REACHED: "trop d'actions en peu de temps. Réessayez plus tard.",
    UPSTREAM_UNREACHABLE: "le service interne ciblé est indisponible.",
    INTERNAL_SERVICE_ERROR: "une erreur interne est survenue sur un service distant.",
};

const normalizeText = (value?: string | null): string => String(value || "").trim();

const includesAny = (source: string, words: string[]): boolean => words.some((word) => source.includes(word));

const resolveErrorKey = (statusCode?: number | null, detail?: string | null, endpoint?: string | null): string => {
    const normalizedDetail = normalizeText(detail).toLowerCase();
    const normalizedEndpoint = normalizeText(endpoint).toLowerCase();

    if (!statusCode) {
        if (includesAny(normalizedDetail, ["timeout", "timed out"])) return "NETWORK_TIMEOUT";
        if (includesAny(normalizedDetail, ["aborted", "abort"])) return "REQUEST_ABORTED";
        if (includesAny(normalizedDetail, ["canceled", "cancelled", "cancel"])) return "REQUEST_CANCELED";
        if (includesAny(normalizedDetail, ["dns", "name or service not known", "enotfound"])) return "DNS_RESOLUTION_FAILED";
        if (includesAny(normalizedDetail, ["ssl", "tls", "certificate"])) return "SSL_ERROR";
        if (normalizedDetail.includes("cors")) return "CORS_BLOCKED";
        if (includesAny(normalizedDetail, ["offline", "network error", "failed to fetch"])) return "OFFLINE";
        return "NETWORK_ERROR";
    }

    if (statusCode === 404) {
        if (includesAny(normalizedDetail, ["user", "utilisateur"]) || normalizedEndpoint.includes("/user")) return "USER_NOT_FOUND";
        if (normalizedDetail.includes("conversation") || normalizedEndpoint.includes("/chat/conversations")) return "CONVERSATION_NOT_FOUND";
        if (includesAny(normalizedDetail, ["friend", "friendship"]) || normalizedEndpoint.includes("/friendships")) return "FRIENDSHIP_NOT_FOUND";
        if (normalizedDetail.includes("notification") || normalizedEndpoint.includes("/notifications")) return "NOTIFICATION_NOT_FOUND";
        if (normalizedDetail.includes("post") || normalizedEndpoint.includes("/posts")) return "POST_NOT_FOUND";
        if (normalizedDetail.includes("comment") || normalizedEndpoint.includes("/comments")) return "COMMENT_NOT_FOUND";
        if (normalizedDetail.includes("message") || normalizedEndpoint.includes("/messages")) return "MESSAGE_NOT_FOUND";
        return "HTTP_404";
    }

    if (statusCode === 410) return "RESOURCE_DELETED";
    if (statusCode === 408 || statusCode === 504) return "NETWORK_TIMEOUT";

    if (statusCode === 409 || statusCode === 422) {
        if (includesAny(normalizedDetail, ["pseudo", "username"])) return "PSEUDO_ALREADY_EXISTS";
        if (normalizedDetail.includes("email") && includesAny(normalizedDetail, ["already", "exist", "duplicate"])) return "EMAIL_ALREADY_EXISTS";
        if (includesAny(normalizedDetail, ["already", "exists", "duplicate"])) return "USER_ALREADY_EXISTS";
        if (includesAny(normalizedDetail, ["required", "missing"])) return "REQUIRED_FIELD_MISSING";
        if (includesAny(normalizedDetail, ["validation", "invalid"])) return "VALIDATION_ERROR";
        return "HTTP_422";
    }

    if (statusCode === 401) {
        if (includesAny(normalizedDetail, ["missing bearer token", "missing token"])) return "MISSING_TOKEN";
        if (includesAny(normalizedDetail, ["expired", "token"])) return "TOKEN_EXPIRED";
        if (includesAny(normalizedDetail, ["invalid", "credentials", "unauthorized"])) return "INVALID_CREDENTIALS";
        return "HTTP_401";
    }

    if (statusCode === 403) {
        if (normalizedDetail.includes("disabled")) return "ACCOUNT_DISABLED";
        if (normalizedDetail.includes("locked")) return "ACCOUNT_LOCKED";
        if (includesAny(normalizedDetail, ["2fa", "totp", "challenge"])) return "TWO_FA_REQUIRED";
        return "HTTP_403";
    }

    if (statusCode === 429) return "RATE_LIMIT_REACHED";
    if (statusCode === 502) return "UPSTREAM_UNREACHABLE";
    if (statusCode === 503) return "INTERNAL_SERVICE_ERROR";

    if (statusCode >= 500) {
        return ERROR_DICTIONARY[`HTTP_${statusCode}`] ? `HTTP_${statusCode}` : "HTTP_5XX_GENERIC";
    }
    if (statusCode >= 400) {
        return ERROR_DICTIONARY[`HTTP_${statusCode}`] ? `HTTP_${statusCode}` : "HTTP_4XX_GENERIC";
    }

    return "NETWORK_ERROR";
};

export const formatApiErrorMessage = ({
    statusCode,
    detail,
    endpoint,
}: ApiErrorFormatOptions): string => {
    const key = resolveErrorKey(statusCode, detail, endpoint);
    const dictionaryMessage = ERROR_DICTIONARY[key] || ERROR_DICTIONARY.NETWORK_ERROR;
    const detailText = normalizeText(detail);

    const label = statusCode
        ? `Erreur ${statusCode}`
        : "Erreur réseau";

    const cleanedDetail = detailText
        .replace(/^failed to call\s+[^:]+:\s*/i, "")
        .replace(/^upstream service unreachable:\s*/i, "")
        .trim();

    if (!cleanedDetail) {
        return `${label}: ${dictionaryMessage}`;
    }

    return `${label}: ${dictionaryMessage} (détail technique: ${cleanedDetail})`;
};
