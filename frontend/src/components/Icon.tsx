import { JSX } from "react";
import { IconButton, IconButtonProps } from "@chakra-ui/react";

interface IconProps extends IconButtonProps
{
    label: string;
    children: React.ReactNode;
}

export const Icon = (
    {children, label, ...props}: IconProps
): JSX.Element => {
    return (
        <IconButton
            boxSize="50px"
            borderRadius="full" 
            variant="ghost" color="text"
            _hover={{ bgColor: "primary", color: "secondary" }}
            aria-label={label}
            {...props}
        >
            {children}
        </IconButton>
    );
};
