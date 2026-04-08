import { ButtonProps, Button } from "@chakra-ui/react";
import { JSX } from "react";

export const CustomButton = (
    { children, label, isNeutral=false, ...props }
    : { children: React.ReactNode, label: string, isNeutral?: boolean } & ButtonProps
): JSX.Element => {
    return (
        <Button
            fontWeight="bold"
            borderRadius="full"
            className="titles-styles"
            borderColor={isNeutral ? "text" : "none"}
            border={isNeutral ? "1px solid" : "none"}
            bg={!isNeutral ? "primary" : "transparent"}
            color={!isNeutral ? "variantSecondary" : "text"}
            justifyContent="flex-start"
            _hover={{ opacity: 0.9 }}
            aria-label={label}
            {...props}
        >
            {children}
        </Button>
    );
};
