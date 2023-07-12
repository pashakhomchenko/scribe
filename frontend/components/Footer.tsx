import NextLink from 'next/link';
import { Text, Link } from '@chakra-ui/react';

export default function Footer() {
  return (
    <footer
      className="flex flex-col justify-center items-center px-6 gap-8 py-8 md:flex-row z-10 relative"
      style={{
        boxShadow:
          '0 -4px 6px -1px rgba(0, 0, 0, 0.1),0 -2px 4px -1px rgba(0, 0, 0, 0.06)'
      }}
    >
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
