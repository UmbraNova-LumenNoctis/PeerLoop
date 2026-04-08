import { useState, JSX } from 'react';
import { LuEye, LuEyeOff } from "react-icons/lu";
import { Field as FormikField } from 'formik';
import { 
    Box, 
    Input, 
    Field, 
    IconButton, 
    InputProps 
} from '@chakra-ui/react';

interface FloatingInputProps extends InputProps
{
    name: string;
    label: string;
    type?: string;
    error?: string;
    isInvalid?: boolean;
    children?: React.ReactNode;
}

export const FloatingInput = ({ name, label, error, type="text", isInvalid=false, children, ...props }: FloatingInputProps): JSX.Element => {
    const [showPassword, setShowPassword] = useState<boolean>(false);
    const currentType = (type != "password") ? "text" : (showPassword ? "text" : "password");

    return (
        <Field.Root invalid={isInvalid}>
            <Box position="relative" w="full">
                <FormikField as={ Input }
                    className="peer text-styles" 
                    id={ name } name={ name } type={currentType}
                    bg="secondary" borderColor="text" borderRadius="xl" 
                    h="50px" px="1rem" pt="1rem"
                    transition="border-color 0.2s"
                    placeholder=" "
                    
                    _hover={{ borderColor: "primary" }}
                    _focus={{ focusRing: "none", borderColor: "primary" }}
                    _invalid={{ borderColor: "error" }}
                    { ...props }
                />

                <Field.Label
                    className="text-styles" htmlFor={ name }
                    position="absolute" left="1rem" top="50%" 
                    transform="translateY(-50%)"
                    transition="all 0.2s ease-out"
                    transformOrigin="left top" 
                    pointerEvents="none"
                    
                    _peerFocus={{
                        top: "0.5rem",
                        transform: "translateY(0) scale(0.8)",
                        color: "primary"
                    }}
                    css={{
                        ".peer:not(:placeholder-shown) ~ &": {
                            top: "0.5rem",
                            transform: "translateY(0) scale(0.8)",
                            color: "primary"
                        }
                    }}
                >{ label }
                </Field.Label>

                {/* Password Toggle Button */}
                {(type == "password") && (
                    <IconButton position="absolute" right="2" top="50%" transform="translateY(-50%)"
                        bgColor="transparent" color="white"
                        onClick={() => setShowPassword(!showPassword)}
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        aria-controls={name}
                    >
                        { showPassword ? <LuEyeOff /> : <LuEye />}
                    </IconButton>
                )}
            </Box>

            {isInvalid && (
                <Field.ErrorText className="text-styles" color="error" aria-live="polite">
                    { error }
                </Field.ErrorText>
            )}

            {children}
        </Field.Root>
    );
};