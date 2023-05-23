import NextLink from 'next/link';
import { Text, Link } from '@chakra-ui/react';

export default function Footer() {
  return (
    <footer className="flex justify-center items-center px-6 gap-8 py-8">
      <Link as={NextLink} href="mailto:tryscribe@gmail.com">
        Contact
      </Link>
      <Link as={NextLink} href="/terms">
        Terms
      </Link>
      <Link as={NextLink} href="/privacy">
        Privacy Policy
      </Link>
      <Text>© 2023 Scribe</Text>
    </footer>
  );
}
