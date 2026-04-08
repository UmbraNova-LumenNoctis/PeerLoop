import { useContext, JSX } from 'react';
import { useNavigate } from 'react-router-dom';
import { Avatar, Circle, Float } from '@chakra-ui/react';
import { UserContext } from '@/context/userContext';

export const User = (
    { name, picture, isOnline = false, userId }
    : { name: string, picture: string, isOnline?: boolean, userId?: string }
): JSX.Element => {
    const navigate = useNavigate();
    const { user } = useContext(UserContext);
    const safeName = name || "";

    return (
        <Avatar.Root 
            colorPalette="green"
            css= { 
                isOnline ? {
                    outline: "2px solid",
                    outlineColor: "green.500",
                    outlineOffset: "2px"
                } : {}
            }
            onClick={() => { const target = userId || user?.id; if (target) navigate(`/profile/${target}`); }}
            cursor="pointer"
        >
            <Avatar.Fallback name={safeName} />
            <Avatar.Image src={picture || undefined} />

            {
                isOnline && (
                    <Float placement="bottom-end" offsetX="1" offsetY="1">
                        <Circle
                            bg="green.500" size="8px"
                            outline="0.2em solid"
                            outlineColor="bg"
                        />
                    </Float>
                )
            }
        </Avatar.Root>
    );
}
