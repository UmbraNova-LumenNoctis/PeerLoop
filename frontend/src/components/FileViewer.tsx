import { LuX } from "react-icons/lu";
import { useMemo, JSX } from "react";
import { FileUpload, Box, Float, Image, Text } from "@chakra-ui/react";

export const FileViewer = (
  { files, setFiles, previewUrl }
  : { files?: File[], setFiles: (files: File[]) => void, previewUrl?: string }
): JSX.Element => {
    const file = files?.[0];

    const fileUrl = useMemo(() => {
        if (file) return (URL.createObjectURL(file));
        return (previewUrl || null);
    }, [files, previewUrl]);

    const isImage =
        files?.[0]?.type?.startsWith("image") ||
        previewUrl?.match(/\.(jpg|jpeg|png|gif|webp|avif)$/i);

    return (
        <FileUpload.ItemGroup flexDirection="row" flexWrap="wrap" gap={5}>

            {file && (
                <FileUpload.Item file={file} w="100%" p="0">
                    <Box w="100%">
                        {
                            isImage 
                            ? <Image src={fileUrl} alt="preview" w="100%" />
                            : <video src={fileUrl} width="100%" controls />
                        }
                    </Box>

                    <Float placement="top-end">
                        <FileUpload.ItemDeleteTrigger onClick={() => setFiles([])} boxSize="5" bg="primary" color="text">
                            <LuX />
                        </FileUpload.ItemDeleteTrigger>
                    </Float>
                </FileUpload.Item>
            )}
            
            {(!file && fileUrl) && (
                <Box w="100%">
                    {
                        isImage 
                        ? <Image src={fileUrl} alt="preview" w="100%" />
                        : <video src={fileUrl} width="100%" controls />
                    }
                </Box>
            )} 
            
            {(!file && !fileUrl) && (
                <Text fontWeight="semibold">No file selected</Text>
            )}

        </FileUpload.ItemGroup>
  );
};