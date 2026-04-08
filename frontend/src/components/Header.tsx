import logo from '@/assets/lg_dark.png';
import { useState, JSX, useEffect, useContext } from "react";
import {
    Box,
    Flex,
    HStack,
    Image,
    IconButton,
    Drawer,
    Portal,
    Stack,
    Text,
    Button,
    Spinner,
} from "@chakra-ui/react";
import { LuMessageCircleMore, LuBell, LuMenu, LuX, LuHouse, LuUsersRound, LuLogOut } from "react-icons/lu";
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { NotificationContext } from "@/context/notificationContext";
import { AuthContext } from '@/context/authContext';
import { UserContext } from '@/context/userContext';
import { SearchBar } from '@/components/SearchBar';
import { User } from '@/components/User';
import useApi from '@/hooks/useAPI';

interface NavLinkProps {
    name: string;
    icon: React.ElementType;
    link: string;
    count?: number;
}

const Links: NavLinkProps[] = [
    {
        name: "Home",
        icon: LuHouse,
        link: "/",
    },
    {
        name: "Invitation",
        icon: LuUsersRound,
        link: "/invitations",
    },
    {
        name: "Message",
        icon: LuMessageCircleMore,
        link: "/chat",
    },
    {
        name: "Notification",
        icon: LuBell,
        link: "/notification",
    }
];

const NavLink = ({ icon: Icon, link, count = 0 }: NavLinkProps) => {
    const location = useLocation();

    return (
        <RouterLink to={link}>
            <IconButton
                variant="ghost"
                borderRadius="full"
                color={location.pathname === link ? "secondary" : "text"}
                bgColor={location.pathname === link ? "primary" : "transparent"}
                _hover={{ bgColor: "primary", color: "secondary" }}
                transition="all 0.3s ease-out"
            >
                <Icon />
                {count > 0 && (
                    <Box
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        position="absolute"
                        top="2px"
                        right="2px"
                        bg="danger"
                        color="white"
                        minW="18px"
                        h="18px"
                        px={1}
                        fontSize="xs"
                        fontWeight="bold"
                        borderRadius="full"
                        border="2px solid"
                        borderColor="secondary"
                        className="text-styles"
                    >
                        {count > 15 ? '15+' : count}
                    </Box>
                )}
            </IconButton>
        </RouterLink>
    );
};

export const Header = (): JSX.Element => {
    const { user } = useContext(UserContext);
    const { logout } = useContext(AuthContext);
    const { counts, refreshNotifications } = useContext(NotificationContext);
    const [openMenu, setOpenMenu] = useState<boolean>(false);

    useEffect(() => {
        refreshNotifications();

        const intervalId = setInterval(() => {
            refreshNotifications();
        }, 15000);

        return () => clearInterval(intervalId);
    }, []);

    useEffect(() => {
        refreshNotifications();
    }, [location.pathname]);

    if (!user) {
        return (
            <Flex
                as="header"
                w="100%"
                h="80px"
                position="fixed"
                top={0}
                left={0}
                zIndex={1200}
                alignItems="center"
                justifyContent="space-between"
                borderBottom="1px solid"
                borderColor="text"
                px={{ base: "5vw", md: "8vw" }}
                bg="secondary"
            >
                <Image src={logo} alt="Image, logo PeerLoop" w="80px" />
                <Spinner color="primary" size="sm" />
            </Flex>
        );
    }

    return (
        <Flex
            as="header"
            w="100%"
            h="80px"
            position="fixed"
            top={0}
            left={0}
            zIndex={1200}
            overflow="visible"
            alignItems="center"
            justifyContent="space-between"
            borderBottom="1px solid"
            borderColor="text"
            px={{ base: "5vw", md: "8vw" }}
            bg="secondary"
        >
            <HStack w="80%" display={{ base: "none", md: "flex" }}>
                <Image src={logo} alt="Image, logo PeerLoop" w="80px" />
                <SearchBar onChanges={() => {}} />
            </HStack>

            <Box display={{ base: "block", lg: "none" }}>
                <Drawer.Root
                    placement="start"
                    open={openMenu}
                    onOpenChange={(e) => setOpenMenu(e.open)}
                >
                    <Drawer.Trigger asChild>
                        <IconButton
                            borderRadius="full"
                            variant="ghost"
                            color="text"
                            display={{ base: "flex", md: "none" }}
                            aria-label="Open Menu"
                            _hover={{ bgColor: "primary", color: "secondary" }}
                            onClick={() => setOpenMenu(true)}
                        >
                            <LuMenu />
                        </IconButton>
                    </Drawer.Trigger>
                    <Portal>
                        <Drawer.Positioner>
                            <Drawer.Content 
                                bg="variantSecondary" 
                                w="100vw" h="100vh" maxW="100vw"
                                opacity={0.95}
                            >
                                <Drawer.Header 
                                    display="flex" 
                                    alignItems="center" 
                                    justifyContent="flex-start"
                                    flexDirection="column"
                                    borderBottom="1px solid"
                                    borderColor="text"
                                    gap={6}
                                    py="24px"
                                >
                                    <HStack gap={3} w="full" justifyContent="space-between">
                                        <Image src={logo} alt="Image, logo PeerLoop" w="50px" />

                                        <IconButton
                                            boxSize="50px"
                                            borderRadius="full"
                                            variant="ghost"
                                            color="text"
                                            aria-label="Close Menu"
                                            _hover={{ bgColor: "primary", color: "secondary" }}
                                            onClick={() => setOpenMenu(false)}
                                        >
                                            <LuX size={28} />
                                        </IconButton>
                                    </HStack>

                                    <RouterLink to="/profile">
                                        <HStack gap="3">
                                            <User name={user.pseudo} picture={user.avatar} />
                                            
                                            <Stack gap="0">
                                                <Text className="title-styles" fontWeight="medium">{user.pseudo}</Text>
                                                <Text className="text-styles">{user.email ? (user.email.length > 25 ? user.email.substring(0, 25) + "..." : user.email) : ""}</Text>
                                            </Stack>
                                        </HStack>
                                    </RouterLink>
                                </Drawer.Header>
                                <Drawer.Body py="24px">
                                    <SearchBar w="full" onChanges={() => setOpenMenu(false)} />
                                </Drawer.Body>
                                <Drawer.Footer p={5}>
                                    <Flex w="full" alignItems="center" justifyContent="center">
                                        <Button 
                                            className="title-styles" 
                                            color="secondary" 
                                            borderRadius="md" 
                                            onClick={logout}
                                            bg="primary" w="50%"
                                        >
                                           <LuLogOut /> Logout
                                        </Button>
                                    </Flex>
                            </Drawer.Footer>
                            </Drawer.Content>
                        </Drawer.Positioner>
                    </Portal>
                </Drawer.Root>
            </Box>

            <HStack as="nav" gap={5}>
                {Links.map((link) => (
                    <NavLink
                        key={link.name}
                        name={link.name}
                        icon={link.icon}
                        link={link.link}
                        count={counts[link.name]}
                    />
                ))}

                <Button 
                    className="title-styles" 
                    color="secondary" 
                    borderRadius="md" 
                    onClick={logout}
                    display={{ base: "none", md: "flex" }}
                    bg="primary"
                >
                    Logout
                </Button>
            </HStack>
        </Flex>
    );
}
