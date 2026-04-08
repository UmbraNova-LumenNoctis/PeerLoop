import { IconButtonProps, IconButton } from "@chakra-ui/react";
import { JSX } from "react";

interface InteractionButtonProps extends IconButtonProps
{
    label: string;
    isActive?: boolean;
    children: React.ReactNode;
}

export const InteractionButton = (
    { children, isActive = false, label, ...props }: InteractionButtonProps
): JSX.Element => {
    return (
        <IconButton 
            w="50%"
            className="title-styles"
            variant="ghost" bg="transparent"
            color={isActive ? "primary" : "text"}
            aria-label={label}
            fontWeight="bold"
            {...props}
        >
            {children}
        </IconButton>
    );
}