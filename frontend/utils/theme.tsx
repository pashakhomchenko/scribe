// theme.ts (tsx file with usage of StyleFunctions, see 4.)
import { extendTheme } from '@chakra-ui/react';
import type { StyleFunctionProps } from '@chakra-ui/styled-system';

const theme = extendTheme({
  components: {
    Button: {
      variants: {
        black: {
          bg: 'black',
          color: 'white',
          _hover: {
            opacity: 0.8
          },
          _loading: {
            opacity: 0.8
          },
          _disabled: {
            opacity: 0.8
          }
        }
      }
    }
  }
});

export default theme;
